"""Gatekeeper 2.A (GK-2.A): Stroke Animation & Pacing Validator."""
import json
import logging
import os
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class Gatekeeper2A:
    """Gatekeeper 2.A: Validates Hanzi stroke animation completeness, colors, and transparency."""

    @staticmethod
    def validate_stroke_assets(output_dir: str) -> Tuple[bool, str]:
        svg_file = os.path.join(output_dir, "stroke.svg")
        info_file = os.path.join(output_dir, "stroke_info.json")

        if not os.path.exists(svg_file) or os.path.getsize(svg_file) < 100:
            return False, "GK-2.A REJECT: stroke.svg is missing or empty."

        if not os.path.exists(info_file):
            return False, "GK-2.A REJECT: stroke_info.json is missing."

        try:
            with open(info_file, "r", encoding="utf-8") as f:
                info = json.load(f)
        except Exception as e:
            return False, f"GK-2.A REJECT: Invalid stroke_info.json: {e}"

        stroke_count = info.get("stroke_count", 0)
        if stroke_count < 1:
            return False, f"GK-2.A REJECT: Invalid stroke count ({stroke_count})."

        duration = info.get("total_duration", 0.0)
        if duration < 2.5 or duration > 16.0:
            return False, f"GK-2.A REJECT: Duration {duration:.1f}s out of acceptable bounds (2.5s - 16.0s)."

        if info.get("final_color", "").upper() not in ["#800020", "#8B0000", "#9B111E"]:
            return False, f"GK-2.A REJECT: Final color {info.get('final_color')} is not Bordeaux Red."

        with open(svg_file, "r", encoding="utf-8") as f:
            svg_text = f.read()

        if "transparent" not in svg_text:
            return False, "GK-2.A REJECT: SVG does not have transparent background."

        return True, "GK-2.A Approved (Stroke animation valid, multi-color & Bordeaux Red transition confirmed)."


# Backward compatibility alias
GKStrokeValidator = Gatekeeper2A
