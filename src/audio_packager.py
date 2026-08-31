"""Audio Packager - Compiles precise audio_timings.json and packages Audio.zip."""
import json
import logging
import os
import zipfile
from typing import Dict, Any

logger = logging.getLogger(__name__)
PAUSE_GAP = 0.35  # Gap between voice tracks in seconds


class AudioPackager:
    """Packages segmented audio files and builds timestamp markers for Step 3."""

    @staticmethod
    def compile_timings_and_zip(durations: Dict[str, float], audio_dir: str, output_zip: str) -> Dict[str, Any]:
        """Calculates chronological timestamps and zips all audio tracks into Audio.zip."""
        timeline = []
        current_time = 0.0

        for key, dur in durations.items():
            start_t = round(current_time, 3)
            end_t = round(start_t + dur, 3)
            timeline.append({
                "file": key,
                "start": start_t,
                "end": end_t,
                "duration": dur
            })
            current_time = end_t + PAUSE_GAP

        total_duration = round(current_time, 2)
        timings_data = {
            "total_video_duration": total_duration,
            "tracks": timeline,
            "track_durations": durations
        }

        timings_path = os.path.join(audio_dir, "audio_timings.json")
        with open(timings_path, "w", encoding="utf-8") as f:
            json.dump(timings_data, f, ensure_ascii=False, indent=2)

        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for key in durations.keys():
                fpath = os.path.join(audio_dir, key)
                if os.path.exists(fpath):
                    zf.write(fpath, arcname=key)
            if os.path.exists(timings_path):
                zf.write(timings_path, arcname="audio_timings.json")

        logger.info(f"📦 Packaged {len(durations)} audio tracks into '{output_zip}' (Total: {total_duration:.1f}s).")
        return timings_data
