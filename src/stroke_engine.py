"""Chinese Stroke Animation Engine - Multi-color, Bordeaux Red Final, Adaptive Pacing."""
import json
import logging
import os
from typing import Dict, Any, List, Optional
from src.stroke_cache import StrokeCache

logger = logging.getLogger(__name__)

RAINBOW_PALETTE = [
    "#E63946", "#F4A261", "#2A9D8F", "#457B9D",
    "#9B5DE5", "#F15BB5", "#00BBF9", "#00F5D4",
    "#DDA15E", "#BC6C25", "#E76F51", "#264653"
]
BORDEAUX_RED = "#800020"


class StrokeEngine:
    """Generates animated Hanzi stroke visuals with adaptive pacing and transparent background."""

    def __init__(self, cache: Optional[StrokeCache] = None):
        self.cache = cache or StrokeCache()

    @staticmethod
    def calculate_duration(stroke_count: int) -> float:
        """Adaptive pacing curve: 1-3 strokes -> 3.5s; 4-5 -> 5.5s; 6-8 -> 8.5s; 9+ -> max 15s."""
        if stroke_count <= 3:
            return 3.5
        elif stroke_count <= 5:
            return 5.5
        elif stroke_count <= 8:
            return 8.5
        else:
            return min(15.0, 8.5 + (stroke_count - 8) * 0.8)

    def generate_stroke_animation(self, character: str, output_dir: str) -> Dict[str, Any]:
        """Generates stroke.svg and stroke_info.json with multi-color & Bordeaux Red transition."""
        os.makedirs(output_dir, exist_ok=True)
        data = self.cache.get_stroke_data(character) or {}
        strokes = data.get("strokes", [])
        stroke_count = len(strokes)
        total_duration = self.calculate_duration(stroke_count)
        stroke_dur = total_duration / max(1, stroke_count)

        # Assign rainbow colors to each stroke
        colors = [RAINBOW_PALETTE[i % len(RAINBOW_PALETTE)] for i in range(stroke_count)]

        svg_paths = []
        for idx, path_d in enumerate(strokes):
            color = colors[idx]
            delay = idx * stroke_dur
            anim_css = (
                f"@keyframes draw_{idx} {{ "
                f"0% {{ opacity: 0; stroke-dashoffset: 1024; stroke: {color}; }} "
                f"20% {{ opacity: 1; stroke-dashoffset: 0; stroke: {color}; }} "
                f"85% {{ stroke: {color}; }} "
                f"100% {{ stroke: {BORDEAUX_RED}; fill: {BORDEAUX_RED}; opacity: 1; }} }}"
            )
            style = (
                f"stroke: {color}; fill: none; stroke-width: 48; stroke-linecap: round; stroke-linejoin: round; "
                f"stroke-dasharray: 1024; stroke-dashoffset: 0; "
                f"animation: draw_{idx} {total_duration}s cubic-bezier(0.4, 0, 0.2, 1) forwards; animation-delay: {delay}s;"
            )
            svg_paths.append((path_d, style, anim_css))

        all_keyframes = "\n".join([item[2] for item in svg_paths])
        path_tags = "\n".join([f'    <path d="{item[0]}" style="{item[1]}" />' for item in svg_paths])

        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024" style="background: transparent;">
  <style>
{all_keyframes}
  </style>
  <g transform="scale(1, -1) translate(0, -900)">
{path_tags}
  </g>
</svg>"""

        svg_path = os.path.join(output_dir, "stroke.svg")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        info = {
            "character": character,
            "stroke_count": stroke_count,
            "total_duration": total_duration,
            "stroke_duration": stroke_dur,
            "stroke_colors": colors,
            "final_color": BORDEAUX_RED,
            "transparency": True,
            "svg_file": "stroke.svg"
        }
        with open(os.path.join(output_dir, "stroke_info.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        logger.info(f"🎨 Generated stroke animation for '{character}' ({stroke_count} strokes, {total_duration:.1f}s).")
        return info
