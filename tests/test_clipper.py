"""
Unit and Integration Tests for Cliptzy Desktop Application Core & Controller.
"""

import unittest
import os
import sys

# Add app root directory to sys.path
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from core.youtube import extract_video_id
from core.config import config, AppConfig
from core.controller import controller, parse_time_to_seconds
from core.utils import is_ffmpeg_available

class TestCliptzyCore(unittest.TestCase):

    def test_extract_video_id(self):
        url1 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        url2 = "https://youtu.be/dQw4w9WgXcQ"
        url3 = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        url_invalid = "https://example.com/invalid"

        self.assertEqual(extract_video_id(url1), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id(url2), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id(url3), "dQw4w9WgXcQ")
        self.assertIsNone(extract_video_id(url_invalid))

    def test_parse_time_to_seconds(self):
        self.assertEqual(parse_time_to_seconds(45), 45)
        self.assertEqual(parse_time_to_seconds("90"), 90)
        self.assertEqual(parse_time_to_seconds("01:30"), 90)
        self.assertEqual(parse_time_to_seconds("01:02:03"), 3723)
        self.assertIsNone(parse_time_to_seconds("invalid"))

    def test_config_persistence(self):
        test_cfg = AppConfig()
        test_cfg.whisper_model = "tiny"
        test_cfg.padding = 15
        test_cfg.set_ratio_preset("1:1")

        test_path = "test_config.json"
        saved = test_cfg.save_to_file(test_path)
        self.assertTrue(saved)

        loaded_cfg = AppConfig()
        loaded = loaded_cfg.load_from_file(test_path)
        self.assertTrue(loaded)
        self.assertEqual(loaded_cfg.whisper_model, "tiny")
        self.assertEqual(loaded_cfg.padding, 15)
        self.assertEqual(loaded_cfg.out_width, 720)
        self.assertEqual(loaded_cfg.out_height, 720)

        if os.path.exists(test_path):
            os.remove(test_path)

    def test_controller_fonts_and_clear_cache(self):
        fonts = controller.get_available_fonts()
        self.assertIsInstance(fonts, list)
        self.assertIn("Arial", fonts)

        res = controller.clear_cache_and_clips()
        self.assertIn("deleted_files", res)
        self.assertIn("deleted_size_mb", res)

    def test_ai_detector_json_parser(self):
        from core.ai_detector import ai_detector
        raw_json_llm = '```json\n[\n  {"start": 10.5, "duration": 25.0, "title": "Gamer Clutch", "reason": "Yelling excited", "score": 0.95}\n]\n```'
        highlights = ai_detector._parse_json_highlights(raw_json_llm)
        self.assertEqual(len(highlights), 1)
        self.assertEqual(highlights[0]["start"], 10.5)
        self.assertEqual(highlights[0]["title"], "Gamer Clutch")

if __name__ == "__main__":
    unittest.main()

