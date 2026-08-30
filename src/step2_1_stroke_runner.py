"""Step 2.1 Chinese Stroke Runner - Generates stroke_order.gif with Gatekeeper 2.A."""
import argparse
import logging
import os
import shutil
import sys
import tempfile
from typing import Optional, Dict, Any

from src.stroke_engine import StrokeEngine
from src.gk_stroke_validator import Gatekeeper2A
from src.gdrive_adapter import GDriveAdapter
from src.sheets_adapter import SheetsAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def process_stroke_for_row(row_info: Dict[str, Any]) -> bool:
    """Executes Step 2.1 Stroke generation flow and uploads GIF to GDrive."""
    row_idx, char = row_info["row_idx"], row_info["character"]
    gfolder_url = row_info.get("gfolder_url", "")
    folder_id = gfolder_url.split("/folders/")[-1].split("?")[0] if "/folders/" in gfolder_url else ""

    logger.info(f"🎨 [Step 2.1] Starting Chinese Stroke Generation for Row {row_idx} ('{char}')...")
    engine, gk_2a, gdrive = StrokeEngine(), Gatekeeper2A(), GDriveAdapter()

    work_dir = tempfile.mkdtemp(prefix=f"step2_1_stroke_{char}_")
    try:
        info = engine.generate_stroke_animation(char, work_dir)
        ok_a, msg_a = gk_2a.validate_stroke_assets(work_dir)
        if not ok_a:
            raise ValueError(f"GK-2.A Failure: {msg_a}")
        logger.info(f"✅ [Step 2.1] GK-2.A Passed for '{char}'.")

        gif_path = os.path.join(work_dir, "stroke_order.gif")
        info_path = os.path.join(work_dir, "stroke_info.json")

        if folder_id:
            logger.info(f"🚀 [Step 2.1] Uploading stroke_order.gif to GDrive folder {folder_id}...")
            gdrive.upload_file_from_disk(gif_path, "stroke_order.gif", folder_id, "image/gif")
            if os.path.exists(info_path):
                gdrive.upload_file_from_disk(info_path, "stroke_info.json", folder_id, "application/json")

        logger.info(f"🎉 STEP 2.1 CHINESE STROKE COMPLETED FOR '{char}' at Row {row_idx}!")
        return True
    except Exception as e:
        logger.error(f"❌ Step 2.1 Error for Row {row_idx} ('{char}'): {e}")
        return False
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run_step2_1_lifecycle(target_row: Optional[int] = None, target_char: Optional[str] = None) -> bool:
    """Lifecycle orchestrator for Step 2.1 Chinese Stroke."""
    sheets = SheetsAdapter()
    if target_row:
        row_info = sheets.get_row_by_index(target_row)
        return process_stroke_for_row(row_info) if row_info else False

    pending_rows = sheets.get_pending_voice_rows()
    if target_char:
        pending_rows = [r for r in pending_rows if r["character"] == target_char]

    if not pending_rows:
        logger.info("ℹ️ No rows pending for Step 2.1 Stroke.")
        return True

    success = True
    for r in pending_rows:
        if not process_stroke_for_row(r):
            success = False
    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 2.1 Chinese Stroke Runner")
    parser.add_argument("--row", type=int, help="Specific row index to process")
    parser.add_argument("--character", type=str, help="Specific character to process")
    args = parser.parse_args()
    ok = run_step2_1_lifecycle(target_row=args.row, target_char=args.character)
    sys.exit(0 if ok else 1)
