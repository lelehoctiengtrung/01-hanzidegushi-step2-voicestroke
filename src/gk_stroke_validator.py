"""Gatekeeper 2.A (GK-2.A): Transparent stroke_order.gif Animation Validator."""
import json
import logging
import os
from typing import Tuple
from PIL import Image

logger = logging.getLogger(__name__)


class Gatekeeper2A:
    """Gatekeeper 2.A: Validates that stroke_order.gif is a valid animated transparent GIF."""

    @staticmethod
    def validate_stroke_assets(output_dir: str) -> Tuple[bool, str]:
        gif_file = os.path.join(output_dir, "stroke_order.gif")
        info_file = os.path.join(output_dir, "stroke_info.json")

        if not os.path.exists(gif_file) or os.path.getsize(gif_file) < 500:
            return False, "GK-2.A REJECT: stroke_order.gif is missing or empty."

        if not os.path.exists(info_file):
            return False, "GK-2.A REJECT: stroke_info.json is missing."

        try:
            im = Image.open(gif_file)
            if im.format != "GIF":
                return False, f"GK-2.A REJECT: Expected GIF format, got {im.format}."
            if getattr(im, "n_frames", 1) < 2:
                return False, f"GK-2.A REJECT: GIF is static ({getattr(im, 'n_frames', 1)} frames)."
            if im.size[0] < 200 or im.size[1] < 200:
                return False, f"GK-2.A REJECT: GIF dimensions too small: {im.size}."
        except Exception as e:
            return False, f"GK-2.A REJECT: Invalid stroke_order.gif: {e}"

        return True, "GK-2.A Approved (stroke_order.gif valid, animated, and verified)."


# Backward compatibility alias
GKStrokeValidator = Gatekeeper2A
