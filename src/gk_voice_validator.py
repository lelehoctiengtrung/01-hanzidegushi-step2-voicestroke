"""Gatekeeper 2.B (GK-2.B): Voice Completeness & Speech Pacing Validator."""
import json
import logging
import os
import zipfile
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

REQUIRED_TRACKS = [
    "vi_part1.wav", "zh_main.mp3", "vi_part2.wav", "vi_vidu.wav",
    "zh_1.mp3", "vi_part3.wav", "zh_2.mp3", "vi_part4.wav"
]


class Gatekeeper2B:
    """Gatekeeper 2.B: Validates completeness of 8 voice tracks, speech rate, and Audio.zip."""

    @staticmethod
    def validate_voice_assets(audio_zip_path: str, timings_data: Dict[str, Any]) -> Tuple[bool, str]:
        if not os.path.exists(audio_zip_path) or os.path.getsize(audio_zip_path) < 500:
            return False, "GK-2.B REJECT: Audio.zip is missing or corrupted."

        # Verify zip contents
        try:
            with zipfile.ZipFile(audio_zip_path, "r") as zf:
                names = zf.namelist()
                for track in REQUIRED_TRACKS:
                    if track not in names:
                        return False, f"GK-2.B REJECT: Missing track '{track}' in Audio.zip."
        except Exception as e:
            return False, f"GK-2.B REJECT: Audio.zip archive error: {e}"

        # Validate total duration
        total_dur = timings_data.get("total_video_duration", 0.0)
        if total_dur < 12.0 or total_dur > 150.0:
            return False, f"GK-2.B REJECT: Total audio duration ({total_dur:.1f}s) out of valid bounds (12s - 150s)."

        # Validate individual track durations
        track_durations = timings_data.get("track_durations", {})
        for track in REQUIRED_TRACKS:
            d = track_durations.get(track, 0.0)
            if d < 0.2:
                return False, f"GK-2.B REJECT: Track '{track}' has invalid duration ({d:.2f}s)."

        return True, "GK-2.B Approved (All 8 voice tracks complete, pacing valid, Audio.zip verified)."


# Backward compatibility alias
GKVoiceValidator = Gatekeeper2B
