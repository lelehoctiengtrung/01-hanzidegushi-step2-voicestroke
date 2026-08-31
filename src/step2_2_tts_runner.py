"""Step 2.2 TTS Voice Runner - OmniVoice (VI) + Edge-TTS (ZH) with Gatekeeper 2.B."""
import argparse
import logging
import os
import re
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
    row_idx, char = row_info["row_idx"], row_info["character"]
    gfolder_url = row_info.get("gfolder_url", "")
    fid = gfolder_url.split("/folders/")[-1].split("?")[0] if "/folders/" in gfolder_url else ""
    logger.info(f"🎙️ [Step 2.2] Starting TTS Synthesis: Row {row_idx} ('{char}')...")
    engine, packager, gk_2b, gdrive, sheets = VoiceEngine(), AudioPackager(), Gatekeeper2B(), GDriveAdapter(), SheetsAdapter()

    stext = gdrive.download_text_file(fid, "voiceover_script.txt") if fid else None
    if not stext and "script_url" in row_info:
        m = re.search(r'[-_\w]{25,}', row_info["script_url"])
        if m:
            stext = gdrive.download_file_by_id(m.group(0))

    script_data = {"character": char, "script_text": stext or "", "meaning": "nghĩa"}
    work_dir = tempfile.mkdtemp(prefix=f"step2_2_tts_{char}_")
    try:
        durations = engine.generate_all_tracks(script_data, work_dir)
        zip_path = os.path.join(work_dir, "Audio.zip")
        timings = packager.compile_timings_and_zip(durations, work_dir, zip_path)
        ok_b, msg_b = gk_2b.validate_voice_assets(zip_path, timings)
        if not ok_b:
            raise ValueError(f"GK-2.B Failure: {msg_b}")
        timings_path = os.path.join(work_dir, "audio_timings.json")
        f_timings = gdrive.upload_file_from_disk(timings_path, "audio_timings.json", fid, "application/json") if fid else {"url": ""}
        f_zip = gdrive.upload_file_from_disk(zip_path, "Audio.zip", fid, "application/zip") if fid else {"url": ""}
        if fid:
            for fname in durations.keys():
                fpath = os.path.join(work_dir, fname)
                mime = "audio/wav" if fname.endswith(".wav") else "audio/mpeg"
                gdrive.upload_file_from_disk(fpath, fname, fid, mime)
        v_url = f_timings.get("url") or f_zip.get("url") or gfolder_url
        sheets.update_voice_complete(row_idx, v_url)
        logger.info(f"🎉 STEP 2.2 TTS DONE: '{char}' Row {row_idx} (Status -> Voice)!")
        return True
    except Exception as e:
        logger.error(f"❌ Step 2.2 Error Row {row_idx} ('{char}'): {e}")
        return False
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run_step2_2_lifecycle(
    target_row: Optional[int] = None,
    target_char: Optional[str] = None,
    start_row: Optional[int] = None,
    end_row: Optional[int] = None
) -> bool:
    sheets = SheetsAdapter()
    if start_row and end_row:
        success = True
        for r_idx in range(start_row, end_row + 1):
            r_info = sheets.get_row_by_index(r_idx)
            if r_info and not process_tts_for_row(r_info):
                success = False
        return success
    if target_row:
        r_info = sheets.get_row_by_index(target_row)
        return process_tts_for_row(r_info) if r_info else False
    rows = sheets.get_pending_voice_rows()
    if target_char:
        rows = [r for r in rows if r["character"] == target_char]
    return all(process_tts_for_row(r) for r in rows) if rows else (logger.info("ℹ️ No pending rows.") or True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 2.2 TTS Voice Runner")
    parser.add_argument("--row", type=int, help="Specific row index")
    parser.add_argument("--character", type=str, help="Specific character")
    parser.add_argument("--start-row", type=int, help="Start row index")
    parser.add_argument("--end-row", type=int, help="End row index")
    args = parser.parse_args()
    ok = run_step2_2_lifecycle(
        target_row=args.row, target_char=args.character, start_row=args.start_row, end_row=args.end_row
    )
    sys.exit(0 if ok else 1)
