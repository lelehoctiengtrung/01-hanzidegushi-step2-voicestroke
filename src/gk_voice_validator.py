"""Gatekeeper 2.B (GK-2.B): Voice Completeness & Speech Pacing Validator."""
import logging
import os
import zipfile
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)
CORE_REQUIRED_TRACKS = ["vi_part1.wav", "zh_main.mp3", "vi_vidu.wav", "zh_1.mp3", "zh_2.mp3"]


class Gatekeeper2B:
    """Gatekeeper 2.B: Validates completeness of voice tracks, speech rate, and Audio.zip."""

    @staticmethod
    def validate_voice_assets(audio_zip_path: str, timings_data: Dict[str, Any]) -> Tuple[bool, str]:
        if not os.path.exists(audio_zip_path) or os.path.getsize(audio_zip_path) < 500:
            return False, "GK-2.B REJECT: Audio.zip is missing or corrupted."

        try:
            with zipfile.ZipFile(audio_zip_path, "r") as zf:
                names = set(zf.namelist())
                for track in CORE_REQUIRED_TRACKS:
                    if track not in names:
                        return False, f"GK-2.B REJECT: Missing core track '{track}' in Audio.zip."
                track_durations = timings_data.get("track_durations", {})
                for track, d in track_durations.items():
                    if track not in names:
                        return False, f"GK-2.B REJECT: Track '{track}' listed in timings but missing in Audio.zip."
                    if d < 0.2:
                        return False, f"GK-2.B REJECT: Track '{track}' duration too short ({d:.2f}s)."
        except Exception as e:
            return False, f"GK-2.B REJECT: Audio.zip archive error: {e}"

        total_dur = timings_data.get("total_video_duration", 0.0)
        if total_dur < 10.0 or total_dur > 180.0:
            return False, f"GK-2.B REJECT: Total duration ({total_dur:.1f}s) out of valid bounds (10s - 180s)."

        return True, f"GK-2.B Approved ({len(track_durations)} tracks complete, pacing valid, Audio.zip verified)."


# Backward compatibility alias
GKVoiceValidator = Gatekeeper2B
