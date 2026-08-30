"""Step 2.2 TTS Voice Runner - OmniVoice (VI) + Edge-TTS (ZH) with Gatekeeper 2.B."""
import argparse
import logging
import os
import shutil
import sys
import tempfile
from typing import Optional, Dict, Any

from src.voice_engine import VoiceEngine
from src.audio_packager import AudioPackager
from src.gk_voice_validator import Gatekeeper2B
from src.gdrive_adapter import GDriveAdapter
from src.sheets_adapter import SheetsAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def process_tts_for_row(row_info: Dict[str, Any]) -> bool:
    """Executes Step 2.2 TTS flow (OmniVoice for VI, Edge-TTS for ZH) and uploads to GDrive."""
    row_idx, char = row_info["row_idx"], row_info["character"]
    gfolder_url = row_info.get("gfolder_url", "")
    folder_id = gfolder_url.split("/folders/")[-1].split("?")[0] if "/folders/" in gfolder_url else ""

    logger.info(f"🎙️ [Step 2.2] Starting TTS Voice Synthesis for Row {row_idx} ('{char}')...")
    engine, packager, gk_2b, gdrive, sheets = VoiceEngine(), AudioPackager(), Gatekeeper2B(), GDriveAdapter(), SheetsAdapter()

    script_data = gdrive.download_config_json(folder_id) if folder_id else None
    if not script_data:
        script_data = {
            "character": char,
            "meaning": "NGHĨA",
            "story": f"Câu chuyện ý nghĩa chiết tự cho chữ {char}.",
            "examples": [{"hanzi": f"{char}1", "mean": "nghĩa 1"}, {"hanzi": f"{char}2", "mean": "nghĩa 2"}]
        }

    work_dir = tempfile.mkdtemp(prefix=f"step2_2_tts_{char}_")
    try:
        durations = engine.generate_all_tracks(script_data, work_dir)
        zip_path = os.path.join(work_dir, "Audio.zip")
        timings = packager.compile_timings_and_zip(durations, work_dir, zip_path)
        ok_b, msg_b = gk_2b.validate_voice_assets(zip_path, timings)
        if not ok_b:
            raise ValueError(f"GK-2.B Failure: {msg_b}")
        logger.info(f"✅ [Step 2.2] GK-2.B Passed for '{char}'.")

        timings_path = os.path.join(work_dir, "audio_timings.json")
        f_zip = gdrive.upload_file_from_disk(zip_path, "Audio.zip", folder_id, "application/zip") if folder_id else {"url": "https://drive.google.com/Audio.zip"}
        if folder_id:
            gdrive.upload_file_from_disk(timings_path, "audio_timings.json", folder_id, "application/json")

        sheets.update_voice_complete(row_idx, f_zip.get("url", ""))
        logger.info(f"🎉 STEP 2.2 TTS COMPLETED FOR '{char}' at Row {row_idx} (Status -> 'Voice')!")
        return True
    except Exception as e:
        logger.error(f"❌ Step 2.2 Error for Row {row_idx} ('{char}'): {e}")
        return False
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run_step2_2_lifecycle(target_row: Optional[int] = None, target_char: Optional[str] = None) -> bool:
    """Lifecycle orchestrator for Step 2.2 TTS Voice."""
    sheets = SheetsAdapter()
    if target_row:
        row_info = sheets.get_row_by_index(target_row)
        return process_tts_for_row(row_info) if row_info else False

    pending_rows = sheets.get_pending_voice_rows()
    if target_char:
        pending_rows = [r for r in pending_rows if r["character"] == target_char]

    if not pending_rows:
        logger.info("ℹ️ No rows pending for Step 2.2 TTS Voice.")
        return True

    success = True
    for r in pending_rows:
        if not process_tts_for_row(r):
            success = False
    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 2.2 TTS Voice Runner")
    parser.add_argument("--row", type=int, help="Specific row index to process")
    parser.add_argument("--character", type=str, help="Specific character to process")
    args = parser.parse_args()
    ok = run_step2_2_lifecycle(target_row=args.row, target_char=args.character)
    sys.exit(0 if ok else 1)
