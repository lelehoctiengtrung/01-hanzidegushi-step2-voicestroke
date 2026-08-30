"""Stroke Cache Manager - Handles offline/cached Hanzi stroke datasets."""
import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "strokes_cache")
CDN_URLS = [
    "https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/{char}.json",
    "https://raw.githubusercontent.com/chanind/hanzi-writer-data/master/data/{char}.json"
]


class StrokeCache:
    """Provides cached stroke SVG paths and medians without redundant downloads."""

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_stroke_data(self, character: str) -> Optional[Dict[str, Any]]:
        char = character.strip()
        if not char:
            return None

        cache_file = os.path.join(self.cache_dir, f"{char}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    logger.info(f"⚡ Loaded stroke data for '{char}' from local cache.")
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Cache read error for '{char}': {e}")

        # Download from CDN on first access and persist into cache
        char_encoded = urllib.parse.quote(char)
        for url_pattern in CDN_URLS:
            url = url_pattern.format(char=char_encoded)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Antigravity-Agent"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    logger.info(f"📥 Downloaded and cached stroke data for '{char}' ({len(data.get('strokes', []))} strokes).")
                    return data
            except Exception:
                continue

        logger.warning(f"Using fallback stroke paths for '{char}'.")
        return {
            "strokes": ["M 100 100 L 900 100", "M 500 100 L 500 900"],
            "medians": [[[100, 100], [900, 100]], [[500, 100], [500, 900]]]
        }
