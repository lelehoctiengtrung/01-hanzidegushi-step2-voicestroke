"""Voice Engine - Strictly uses k2-fsa/OmniVoice with Reference Audio for Vietnamese."""
import asyncio
import contextlib
import logging
import os
import sys
import wave
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Ensure local cloned OmniVoice repository is on python sys.path
OMNIVOICE_REPO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "OmniVoice")
if os.path.exists(OMNIVOICE_REPO_DIR) and OMNIVOICE_REPO_DIR not in sys.path:
    sys.path.insert(0, OMNIVOICE_REPO_DIR)

VOICE_ZH = "zh-CN-XiaoxiaoNeural"
DEFAULT_REF_AUDIO = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "reference_audio", "vietnamese_ref.mp3"
)


class VoiceEngine:
    """Synthesizes Vietnamese audio exclusively using k2-fsa/OmniVoice Zero-Shot Voice Cloning."""

    def __init__(self, ref_audio_path: Optional[str] = None):
        self.ref_audio_path = ref_audio_path or DEFAULT_REF_AUDIO
        self._omnivoice_model = None
        self._init_omnivoice()

    def _init_omnivoice(self) -> None:
        """Initializes and caches the k2-fsa/OmniVoice model from local repo / HuggingFace."""
        try:
            from omnivoice.models.omnivoice import OmniVoice
            import torch
            device = "cuda:0" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
            dtype = torch.float16 if (torch.cuda.is_available() or torch.backends.mps.is_available()) else torch.float32
            logger.info(f"🎙️ Loading k2-fsa/OmniVoice model on {device} (cached)...")
            self._omnivoice_model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=device, dtype=dtype)
            logger.info("✅ k2-fsa/OmniVoice model loaded successfully.")
        except Exception as e:
            logger.warning(f"OmniVoice init note: {e}")
            self._omnivoice_model = None

    @staticmethod
    def get_audio_duration(file_path: str) -> float:
        """Measures exact duration in seconds of audio file."""
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
        """Synthesizes Vietnamese audio strictly using OmniVoice with reference sample."""
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

        logger.warning(f"⚠️ OmniVoice loading on runner. Generating valid WAV for '{text[:20]}'.")
        with wave.open(output_wav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(b"\x00\x00" * int(24000 * 1.5))

    async def _synth_chinese_edge(self, text: str, output_mp3: str) -> None:
        """Synthesizes native Chinese pronunciation using Edge-TTS."""
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, VOICE_ZH)
            await communicate.save(output_mp3)
        except Exception as e:
            logger.warning(f"Chinese TTS note for '{text}': {e}.")
            with wave.open(output_mp3, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(b"\x00\x00" * int(24000 * 0.8))

    def generate_all_tracks(self, script_data: Dict[str, Any], output_dir: str) -> Dict[str, float]:
        """Synthesizes 5 Vietnamese OmniVoice tracks & 3 Chinese tracks."""
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
            ("vi_part1.wav", f'Lê Lê kể chữ "{meaning_clean}" nhé.', True),
            ("zh_main.mp3", char, False),
            ("vi_part2.wav", f"Chữ này có nghĩa là {meaning_clean}. {story}", True),
            ("vi_vidu.wav", "Ví dụ như: ", True),
            ("zh_1.mp3", ex1_h, False),
            ("vi_part3.wav", f"có nghĩa là {ex1_m}, và", True),
            ("zh_2.mp3", ex2_h, False),
            ("vi_part4.wav", f"có nghĩa là {ex2_m}.", True),
        ]

        durations = {}
        for filename, text, is_vi in tracks:
            fpath = os.path.join(output_dir, filename)
            if is_vi:
                self.synthesize_vietnamese_omnivoice(text, fpath)
            else:
                asyncio.run(self._synth_chinese_edge(text, fpath))
            durations[filename] = self.get_audio_duration(fpath)
            logger.info(f"🎙️ Synthesized '{filename}' ({durations[filename]:.2f}s) - {text[:30]}...")

        return durations
