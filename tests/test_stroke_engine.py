"""Unit Tests for Stroke Engine & Gatekeeper 2.A."""
import os
import shutil
import tempfile
import unittest
from src.stroke_engine import StrokeEngine
from src.gk_stroke_validator import Gatekeeper2A


class TestStrokeEngine(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.engine = StrokeEngine()
        self.gk_2a = Gatekeeper2A()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pacing_curve(self):
        self.assertEqual(StrokeEngine.calculate_duration(1), 3.5)
        self.assertEqual(StrokeEngine.calculate_duration(3), 3.5)
        self.assertEqual(StrokeEngine.calculate_duration(4), 5.5)
        self.assertEqual(StrokeEngine.calculate_duration(8), 8.5)
        self.assertLessEqual(StrokeEngine.calculate_duration(20), 15.0)

    def test_stroke_generation_and_gk2a(self):
        info = self.engine.generate_stroke_animation("门", self.temp_dir)
        self.assertIn("character", info)
        self.assertEqual(info["final_color"], "#800020")
        self.assertTrue(info["transparency"])

        ok, msg = self.gk_2a.validate_stroke_assets(self.temp_dir)
        self.assertTrue(ok, f"GK-2.A failed: {msg}")


if __name__ == "__main__":
    unittest.main()
