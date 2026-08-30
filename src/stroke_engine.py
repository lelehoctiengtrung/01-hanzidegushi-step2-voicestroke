"""Chinese Stroke Animation Engine - Authentic HanziWriter Calligraphy ClipPath Algorithm."""
import json
import logging
import math
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
    """Generates authentic Hanzi stroke animations using clip-path masking and brush medians."""

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
        """Generates authentic calligraphy stroke.svg with clip-path masks, multi-color & Bordeaux Red."""
        os.makedirs(output_dir, exist_ok=True)
        data = self.cache.get_stroke_data(character) or {}
        strokes = data.get("strokes", [])
        medians = data.get("medians", [])
        stroke_count = len(strokes)
        total_duration = self.calculate_duration(stroke_count)
        stroke_dur = total_duration / max(1, stroke_count)

        colors = [RAINBOW_PALETTE[i % len(RAINBOW_PALETTE)] for i in range(stroke_count)]
        clip_defs, anim_paths, all_css = [], [], []

        for idx, (stroke_outline, median_pts) in enumerate(zip(strokes, medians)):
            color = colors[idx]
            delay = idx * stroke_dur

            # Build median path string
            if median_pts:
                med_d = f"M {median_pts[0][0]} {median_pts[0][1]} " + " ".join([f"L {p[0]} {p[1]}" for p in median_pts[1:]])
                length = sum(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) for p1, p2 in zip(median_pts[:-1], median_pts[1:]))
            else:
                med_d = stroke_outline
                length = 500.0
            dash_len = max(length * 1.6, 600.0)

            clip_defs.append(f'    <clipPath id="clip-{idx}"><path d="{stroke_outline}" /></clipPath>')

            anim_css = (
                f"@keyframes draw_stroke_{idx} {{ "
                f"0% {{ stroke-dashoffset: {dash_len:.0f}; stroke: {color}; opacity: 0; }} "
                f"5% {{ opacity: 1; }} "
                f"75% {{ stroke-dashoffset: 0; stroke: {color}; }} "
                f"90% {{ stroke: {color}; }} "
                f"100% {{ stroke-dashoffset: 0; stroke: {BORDEAUX_RED}; opacity: 1; }} }}"
            )
            all_css.append(anim_css)

            path_tag = (
                f'<path d="{med_d}" clip-path="url(#clip-{idx})" stroke="{color}" stroke-width="140" '
                f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{dash_len:.0f}" '
                f'stroke-dashoffset="{dash_len:.0f}" '
                f'style="animation: draw_stroke_{idx} {total_duration:.2f}s cubic-bezier(0.4, 0, 0.2, 1) forwards; '
                f'animation-delay: {delay:.2f}s;" />'
            )
            anim_paths.append(f"    {path_tag}")

        defs_str = "\n".join(clip_defs)
        css_str = "\n".join(all_css)
        paths_str = "\n".join(anim_paths)

        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="500" height="500" style="background: transparent;">
  <defs>
{defs_str}
  </defs>
  <style>
{css_str}
  </style>
  <g transform="scale(1, -1) translate(0, -900)">
{paths_str}
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

        logger.info(f"🎨 Generated authentic calligraphy stroke for '{character}' ({stroke_count} strokes, {total_duration:.1f}s).")
        return info
