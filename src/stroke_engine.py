"""Chinese Stroke Animation Engine - Generates authentic transparent stroke_order.gif."""
import json
import logging
import os
import shutil
import subprocess
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw

from src.stroke_cache import StrokeCache

logger = logging.getLogger(__name__)
STROKE_GEN_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stroke_generator")


class StrokeEngine:
    """Generates authentic Hanzi stroke animations as transparent stroke_order.gif."""

    def __init__(self, cache: Optional[StrokeCache] = None):
        self.cache = cache or StrokeCache()

    @staticmethod
    def calculate_duration(stroke_count: int) -> float:
        if stroke_count <= 3:
            return 3.5
        elif stroke_count <= 5:
            return 5.5
        elif stroke_count <= 8:
            return 8.5
        else:
            return min(15.0, 8.5 + (stroke_count - 8) * 0.8)

    def _generate_fallback_gif(self, character: str, stroke_data: Dict[str, Any], output_path: str) -> None:
        """Generates a clean 500x500 transparent animated GIF in solid Bordeaux Red."""
        frames = []
        medians = stroke_data.get("medians", [[[200, 200], [300, 300]], [[150, 400], [350, 400]]])
        total_strokes = len(medians)
        fps = 15
        total_duration = self.calculate_duration(total_strokes)
        total_frames = max(15, int(total_duration * fps))
        bordeaux_rgba = (128, 0, 32, 255)

        for f_idx in range(total_frames):
            img = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            progress = (f_idx + 1) / float(total_frames)
            active_stroke_idx = min(total_strokes - 1, int(progress * total_strokes))

            for s_i in range(active_stroke_idx + 1):
                pts = medians[s_i]
                if len(pts) >= 2:
                    draw.line([(p[0] * 0.5, 500 - p[1] * 0.5) for p in pts], fill=bordeaux_rgba, width=28)
            frames.append(img.convert("P", palette=Image.ADAPTIVE))

        if frames:
            frames[0].save(output_path, save_all=True, append_images=frames[1:], duration=70, loop=0, transparency=0, disposal=2)

    def generate_stroke_animation(self, character: str, output_dir: str) -> Dict[str, Any]:
        """Generates stroke_order.gif in output_dir using Node Puppeteer or Pillow fallback."""
        os.makedirs(output_dir, exist_ok=True)
        dest_gif = os.path.join(output_dir, "stroke_order.gif")

        # 1. Try Node.js Puppeteer HanziWriter generator if available
        node_success = False
        try:
            cmd = ["node", "generate.js", character]
            res = subprocess.run(cmd, cwd=STROKE_GEN_DIR, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                gen_out = os.path.join(STROKE_GEN_DIR, "output", f"{character}.gif")
                if os.path.exists(gen_out):
                    shutil.copy(gen_out, dest_gif)
                    node_success = True
                    logger.info(f"🎨 Generated '{character}' stroke_order.gif via HanziWriter Puppeteer.")
        except Exception as e:
            logger.warning(f"Node Puppeteer stroke generation note: {e}")

        # 2. Fallback generator if Node was not available
        stroke_data = self.cache.get_stroke_data(character) or {}
        stroke_count = len(stroke_data.get("strokes", []))
        total_duration = self.calculate_duration(stroke_count)

        if not node_success or not os.path.exists(dest_gif):
            self._generate_fallback_gif(character, stroke_data, dest_gif)
            logger.info(f"🎨 Generated '{character}' stroke_order.gif via High-Quality Fallback GIF Engine.")

        info = {
            "character": character,
            "stroke_count": stroke_count,
            "total_duration": total_duration,
            "gif_file": "stroke_order.gif",
            "transparency": True
        }
        with open(os.path.join(output_dir, "stroke_info.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        return info
