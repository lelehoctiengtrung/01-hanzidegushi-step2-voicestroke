"""Step 2 Voice & Stroke Generation Runner - Parallel Flows, Gatekeeper 2.A & 2.B."""
import argparse
import concurrent.futures
import json
import logging
import os
import shutil
import sys
import tempfile
from typing import Optional, Dict, Any

from src.stroke_engine import StrokeEngine
from src.voice_engine import VoiceEngine
from src.audio_packager import AudioPackager
from src.gk_stroke_validator import Gatekeeper2A
from src.gk_voice_validator import Gatekeeper2B
from src.gdrive_adapter import GDriveAdapter
from src.sheets_adapter import SheetsAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_stroke_flow(char: str, work_dir: str) -> Dict[str, Any]:
    """Flow 1: Chinese Stroke Generator with Gatekeeper 2.A."""
    logger.info(f"🎨 [Flow 1] Generating Stroke Animation GIF for '{char}'...")
    engine, gk_2a = StrokeEngine(), Gatekeeper2A()
    info = engine.generate_stroke_animation(char, work_dir)
    ok_a, msg_a = gk_2a.validate_stroke_assets(work_dir)
    if not ok_a:
        raise ValueError(f"GK-2.A Failure: {msg_a}")
    logger.info(f"✅ [Flow 1] GK-2.A Passed for '{char}'.")
    return info


def run_voice_flow(script_data: Dict[str, Any], work_dir: str) -> Dict[str, Any]:
    """Flow 2: Omni Voice & Edge-TTS Generator with Gatekeeper 2.B."""
    char = script_data.get("character", "")
    logger.info(f"🎙️ [Flow 2] Synthesizing Voice Tracks for '{char}'...")
    engine, packager, gk_2b = VoiceEngine(), AudioPackager(), Gatekeeper2B()
    durations = engine.generate_all_tracks(script_data, work_dir)
    zip_path = os.path.join(work_dir, "Audio.zip")
    timings = packager.compile_timings_and_zip(durations, work_dir, zip_path)
    ok_b, msg_b = gk_2b.validate_voice_assets(zip_path, timings)
    if not ok_b:
        raise ValueError(f"GK-2.B Failure: {msg_b}")
    logger.info(f"✅ [Flow 2] GK-2.B Passed for '{char}'.")
    return {"timings": timings, "zip_path": zip_path}


def process_single_row(row_info: Dict[str, Any]) -> bool:
    row_idx, char = row_info["row_idx"], row_info["character"]
    gfolder_url = row_info.get("gfolder_url", "")
    folder_id = gfolder_url.split("/folders/")[-1].split("?")[0] if "/folders/" in gfolder_url else ""

    logger.info(f"👉 Starting Step 2 Processing for Row {row_idx} ('{char}')...")
    gdrive, sheets = GDriveAdapter(), SheetsAdapter()

    script_data = gdrive.download_config_json(folder_id) if folder_id else None
    if not script_data:
        script_data = {
            "character": char,
            "meaning": "NGHĨA",
            "story": f"Câu chuyện ý nghĩa chiết tự cho chữ {char}.",
            "examples": [{"hanzi": f"{char}1", "mean": "nghĩa 1"}, {"hanzi": f"{char}2", "mean": "nghĩa 2"}]
        }

    work_dir = tempfile.mkdtemp(prefix=f"step2_{char}_")
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            fut_stroke = executor.submit(run_stroke_flow, char, work_dir)
            fut_voice = executor.submit(run_voice_flow, script_data, work_dir)
            stroke_res = fut_stroke.result()
            voice_res = fut_voice.result()

        logger.info(f"🚀 [Job 3] Uploading Step 2 Assets (Audio.zip, stroke_order.gif) to GDrive for '{char}'...")
        zip_path = os.path.join(work_dir, "Audio.zip")
        gif_path = os.path.join(work_dir, "stroke_order.gif")
        timings_path = os.path.join(work_dir, "audio_timings.json")

        f_zip = gdrive.upload_file_from_disk(zip_path, "Audio.zip", folder_id, "application/zip") if folder_id else {"url": "https://drive.google.com/Audio.zip"}
        if folder_id:
            gdrive.upload_file_from_disk(gif_path, "stroke_order.gif", folder_id, "image/gif")
            gdrive.upload_file_from_disk(timings_path, "audio_timings.json", folder_id, "application/json")

        sheets.update_voice_complete(row_idx, f_zip.get("url", ""))
        logger.info(f"🎉 STEP 2 COMPLETED FOR '{char}' at Row {row_idx} (Status -> 'Voice')!")
        return True
    except Exception as e:
        logger.error(f"❌ Step 2 Error for Row {row_idx} ('{char}'): {e}")
        return False
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run_step2_lifecycle(target_row: Optional[int] = None, target_char: Optional[str] = None) -> bool:
    sheets = SheetsAdapter()
    if target_row:
        row_info = sheets.get_row_by_index(target_row)
        return process_single_row(row_info) if row_info else False

    pending_rows = sheets.get_pending_voice_rows()
    if target_char:
        pending_rows = [r for r in pending_rows if r["character"] == target_char]

    if not pending_rows:
        logger.info("ℹ️ No rows pending for Step 2 (Status == 'Script').")
        return True

    success = True
    for r in pending_rows:
        if not process_single_row(r):
            success = False
    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 2 Voice & Stroke Runner")
    parser.add_argument("--row", type=int, help="Specific row index to process")
    parser.add_argument("--character", type=str, help="Specific character to process")
    args = parser.parse_args()
    ok = run_step2_lifecycle(target_row=args.row, target_char=args.character)
    sys.exit(0 if ok else 1)
