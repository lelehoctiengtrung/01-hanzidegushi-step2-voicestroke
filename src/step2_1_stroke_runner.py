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
    row_idx, char = row_info["row_idx"], row_info["character"]
    gfolder_url = row_info.get("gfolder_url", "")
    fid = gfolder_url.split("/folders/")[-1].split("?")[0] if "/folders/" in gfolder_url else ""

    logger.info(f"🎨 [Step 2.1] Starting Stroke Gen for Row {row_idx} ('{char}')...")
    engine, gk_2a, gdrive = StrokeEngine(), Gatekeeper2A(), GDriveAdapter()
    work_dir = tempfile.mkdtemp(prefix=f"step2_1_stroke_{char}_")
    try:
        info = engine.generate_stroke_animation(char, work_dir)
        ok_a, msg_a = gk_2a.validate_stroke_assets(work_dir)
        if not ok_a:
            raise ValueError(f"GK-2.A Failure: {msg_a}")
        gif_path = os.path.join(work_dir, "stroke_order.gif")
        info_path = os.path.join(work_dir, "stroke_info.json")
        if fid:
            gdrive.upload_file_from_disk(gif_path, "stroke_order.gif", fid, "image/gif")
            if os.path.exists(info_path):
                gdrive.upload_file_from_disk(info_path, "stroke_info.json", fid, "application/json")
        logger.info(f"🎉 STEP 2.1 STROKE DONE: '{char}' Row {row_idx}!")
        return True
    except Exception as e:
        logger.error(f"❌ Step 2.1 Error Row {row_idx} ('{char}'): {e}")
        return False
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run_step2_1_lifecycle(
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
            if r_info and not process_stroke_for_row(r_info):
                success = False
        return success
    if target_row:
        r_info = sheets.get_row_by_index(target_row)
        return process_stroke_for_row(r_info) if r_info else False
    rows = sheets.get_pending_voice_rows()
    if target_char:
        rows = [r for r in rows if r["character"] == target_char]
    return all(process_stroke_for_row(r) for r in rows) if rows else (logger.info("ℹ️ No pending rows.") or True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 2.1 Chinese Stroke Runner")
    parser.add_argument("--row", type=int, help="Specific row index")
    parser.add_argument("--character", type=str, help="Specific character")
    parser.add_argument("--start-row", type=int, help="Start row index")
    parser.add_argument("--end-row", type=int, help="End row index")
    args = parser.parse_args()
    ok = run_step2_1_lifecycle(
        target_row=args.row, target_char=args.character, start_row=args.start_row, end_row=args.end_row
    )
    sys.exit(0 if ok else 1)
