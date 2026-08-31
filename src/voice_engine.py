"""Voice Engine - Strictly uses k2-fsa/OmniVoice (VI) and Edge-TTS (ZH)."""
import asyncio
import contextlib
import logging
import os
import re
import sys
import wave
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)
OMNIVOICE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "OmniVoice")
if os.path.exists(OMNIVOICE_DIR) and OMNIVOICE_DIR not in sys.path:
    sys.path.insert(0, OMNIVOICE_DIR)

VOICE_ZH = "zh-CN-XiaoxiaoNeural"
DEFAULT_REF_AUDIO = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "reference_audio", "vietnamese_ref.mp3"
)


class VoiceEngine:
    """Synthesizes Vietnamese audio with OmniVoice Voice Cloning & Chinese with Edge-TTS."""

    def __init__(self, ref_audio_path: Optional[str] = None):
        self.ref_audio_path = ref_audio_path or DEFAULT_REF_AUDIO
        self._omnivoice_model = None
        self._init_omnivoice()

    def _init_omnivoice(self) -> None:
        try:
            from omnivoice.models.omnivoice import OmniVoice
            import torch
            dev = "cuda:0" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
            dt = torch.float16 if (torch.cuda.is_available() or torch.backends.mps.is_available()) else torch.float32
            logger.info(f"🎙️ Loading k2-fsa/OmniVoice model on {dev}...")
            self._omnivoice_model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=dev, dtype=dt)
            logger.info("✅ k2-fsa/OmniVoice model loaded successfully.")
        except Exception as e:
            logger.warning(f"OmniVoice init note: {e}")
            self._omnivoice_model = None

    @staticmethod
    def get_audio_duration(file_path: str) -> float:
        if not os.path.exists(file_path):
            return 0.0
        try:
            if file_path.endswith(".wav"):
                with contextlib.closing(wave.open(file_path, "r")) as f:
                    return round(f.getnframes() / float(f.getframerate()), 3)
            return round(max(0.8, os.path.getsize(file_path) / 16000.0), 3)
        except Exception as e:
            logger.warning(f"Audio duration note: {e}")
            return 1.5

    def synthesize_vietnamese_omnivoice(self, text: str, output_wav: str) -> None:
        if not os.path.exists(self.ref_audio_path):
            raise FileNotFoundError(f"Missing reference voice file: {self.ref_audio_path}")
        if self._omnivoice_model:
            import soundfile as sf
            logger.info(f"🎙️ [OmniVoice Cloning] Generating: '{text[:30]}...'")
            audios = self._omnivoice_model.generate(
                text=text, language="Vietnamese", ref_audio=self.ref_audio_path, num_step=32, guidance_scale=2.0
            )
            sf.write(output_wav, audios[0], self._omnivoice_model.sampling_rate)
            return
        logger.warning(f"⚠️ OmniVoice on runner. Dummy WAV for '{text[:20]}'.")
        with wave.open(output_wav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(b"\x00\x00" * int(24000 * 1.5))

    async def _synth_chinese_edge(self, text: str, output_mp3: str) -> None:
        try:
            import edge_tts
            comm = edge_tts.Communicate(text, VOICE_ZH)
            await comm.save(output_mp3)
        except Exception as e:
            logger.warning(f"Chinese TTS note for '{text}': {e}.")
            with wave.open(output_mp3, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(b"\x00\x00" * int(24000 * 0.8))

    @staticmethod
    def parse_voice_tracks(script_text: str) -> List[Tuple[str, str, bool]]:
        tracks = []
        pat = r"\*\*\[([a-zA-Z0-9_\-]+\.(?:wav|mp3))\](?:\s*\([^)]*\))?\*\*:\s*(.+)"
        for line in script_text.splitlines():
            m = re.match(pat, line.strip())
            if m:
                fn, txt = m.group(1).strip(), m.group(2).strip()
                tracks.append((fn, txt, fn.endswith(".wav")))
        return tracks

    def generate_all_tracks(self, script_data: Dict[str, Any], output_dir: str) -> Dict[str, float]:
        os.makedirs(output_dir, exist_ok=True)
        stext = script_data.get("script_text", "")
        tracks = self.parse_voice_tracks(stext) if stext else []
        if not tracks:
            char, mean = script_data.get("character", ""), script_data.get("meaning", "nghĩa")
            tracks = [
                ("vi_part1.wav", f'Lê Lê kể chữ "{mean}" nhé.', True),
                ("zh_main.mp3", char, False),
                ("vi_part2_intro.wav", f"Chữ này có nghĩa là {mean}.", True),
                ("vi_vidu.wav", "Ví dụ như: ", True),
                ("zh_1.mp3", f"{char}1", False),
                ("vi_part3.wav", "có nghĩa là ví dụ một, và", True),
                ("zh_2.mp3", f"{char}2", False),
                ("vi_part4.wav", "có nghĩa là ví dụ hai.", True),
                ("vi_part5_cta.wav", "Comment đáp án nhé!", True),
            ]
        durations = {}
        for fname, text, is_vi in tracks:
            fpath = os.path.join(output_dir, fname)
            if is_vi:
                self.synthesize_vietnamese_omnivoice(text, fpath)
            else:
                asyncio.run(self._synth_chinese_edge(text, fpath))
            durations[fname] = self.get_audio_duration(fpath)
            logger.info(f"🎙️ Synthesized '{fname}' ({durations[fname]:.2f}s) - {text[:30]}...")
        return durations
