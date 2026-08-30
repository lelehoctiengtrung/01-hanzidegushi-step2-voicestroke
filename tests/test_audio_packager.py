"""Unit Tests for Audio Packager & Gatekeeper 2.B."""
import os
import shutil
import tempfile
import unittest
from src.audio_packager import AudioPackager, TRACK_KEYS
from src.gk_voice_validator import Gatekeeper2B


class TestAudioPackager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.packager = AudioPackager()
        self.gk_2b = Gatekeeper2B()

        # Create dummy mock audio files
        for track in TRACK_KEYS:
            with open(os.path.join(self.temp_dir, track), "wb") as f:
                f.write(b"mock_audio_content_1234567890" * 20)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_packager_and_gk2b(self):
        durations = {k: 2.0 for k in TRACK_KEYS}
        zip_path = os.path.join(self.temp_dir, "Audio.zip")
        timings = self.packager.compile_timings_and_zip(durations, self.temp_dir, zip_path)

        self.assertIn("total_video_duration", timings)
        self.assertEqual(len(timings["tracks"]), 8)
        self.assertTrue(os.path.exists(zip_path))

        ok, msg = self.gk_2b.validate_voice_assets(zip_path, timings)
        self.assertTrue(ok, f"GK-2.B failed: {msg}")


if __name__ == "__main__":
    unittest.main()
