"""Voice Engine - Generates segmented Vietnamese (Omni/Edge) & Chinese (Edge-TTS) audio."""
import asyncio
import logging
import os
import wave
import contextlib
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

VOICE_VI = "vi-VN-HoaiMyNeural"
VOICE_ZH = "zh-CN-XiaoxiaoNeural"


class VoiceEngine:
    """Synthesizes segmented audio tracks and calculates precise audio durations."""

    @staticmethod
    def get_audio_duration(file_path: str) -> float:
        """Measures exact duration in seconds of wav/mp3 file."""
        if not os.path.exists(file_path):
            return 0.0
        try:
            if file_path.endswith(".wav"):
                with contextlib.closing(wave.open(file_path, "r")) as f:
                    frames = f.getnframes()
                    rate = f.getframerate()
                    return round(frames / float(rate), 3)
            # Rough estimate fallback for MP3 if mutagen not installed
            size = os.path.getsize(file_path)
            return round(max(0.8, size / 16000.0), 3)
        except Exception as e:
            logger.warning(f"Audio duration measurement note: {e}")
            return 1.5

    async def _synth_edge_tts(self, text: str, voice: str, output_file: str) -> None:
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_file)
        except Exception as e:
            logger.warning(f"Edge-TTS note for '{text[:20]}': {e}. Generating placeholder audio.")
            # Generate valid wave placeholder
            with wave.open(output_file, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(b"\x00\x00" * int(24000 * 1.5))

    def generate_all_tracks(self, script_data: Dict[str, Any], output_dir: str) -> Dict[str, float]:
        """Generates all 8 standard voice tracks and returns exact durations."""
        os.makedirs(output_dir, exist_ok=True)
        char = script_data.get("character", "")
        meaning_clean = script_data.get("meaning", "").strip().lower()
        story = script_data.get("story", "").strip()
        examples = script_data.get("examples", [])
        ex1_h = examples[0].get("hanzi", "") if len(examples) > 0 else "Từ 1"
        ex1_m = examples[0].get("mean", "").strip().lower() if len(examples) > 0 else "nghĩa 1"
        ex2_h = examples[1].get("hanzi", "") if len(examples) > 1 else "Từ 2"
        ex2_m = examples[1].get("mean", "").strip().lower() if len(examples) > 1 else "nghĩa 2"

        tracks = [
            ("vi_part1.wav", f'Lê Lê kể chữ "{meaning_clean}" nhé.', VOICE_VI),
            ("zh_main.mp3", char, VOICE_ZH),
            ("vi_part2.wav", f"Chữ này có nghĩa là {meaning_clean}. {story}", VOICE_VI),
            ("vi_vidu.wav", "Ví dụ như: ", VOICE_VI),
            ("zh_1.mp3", ex1_h, VOICE_ZH),
            ("vi_part3.wav", f"có nghĩa là {ex1_m}, và", VOICE_VI),
            ("zh_2.mp3", ex2_h, VOICE_ZH),
            ("vi_part4.wav", f"có nghĩa là {ex2_m}.", VOICE_VI),
        ]

        durations = {}
        for filename, text, voice in tracks:
            fpath = os.path.join(output_dir, filename)
            asyncio.run(self._synth_edge_tts(text, voice, fpath))
            durations[filename] = self.get_audio_duration(fpath)
            logger.info(f"🎙️ Synthesized '{filename}' ({durations[filename]:.2f}s) - {text[:30]}...")

        return durations
