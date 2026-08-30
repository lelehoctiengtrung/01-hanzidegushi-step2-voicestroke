"""Unit Tests for Step 2 Runner & Parallel Flows."""
import os
import shutil
import tempfile
import unittest
from src.step2_runner import run_stroke_flow, run_voice_flow


class TestStep2Runner(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_stroke_flow(self):
        info = run_stroke_flow("门", self.temp_dir)
        self.assertEqual(info["character"], "门")
        self.assertEqual(info["final_color"], "#800020")

    def test_run_voice_flow(self):
        script_data = {
            "character": "门",
            "meaning": "CÁNH CỬA",
            "story": "Một cánh cửa mở ra thế giới mới.",
            "examples": [{"hanzi": "门口", "mean": "cổng vào"}, {"hanzi": "门票", "mean": "vé vào cửa"}]
        }
        res = run_voice_flow(script_data, self.temp_dir)
        self.assertIn("timings", res)
        self.assertIn("zip_path", res)
        self.assertTrue(os.path.exists(res["zip_path"]))


if __name__ == "__main__":
    unittest.main()
