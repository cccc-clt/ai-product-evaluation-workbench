import os
import unittest
from unittest.mock import patch

from src.config import get_settings, is_api_configured


class ConfigTests(unittest.TestCase):
    def test_placeholder_api_key_is_not_configured(self):
        with patch.dict(os.environ, {"API_KEY": "your_api_key_here"}, clear=False):
            settings = get_settings()

        self.assertFalse(is_api_configured(settings))

    def test_invalid_numeric_env_values_fall_back_to_defaults(self):
        with patch.dict(
            os.environ,
            {
                "DEFAULT_TEMPERATURE": "not-a-number",
                "DEFAULT_MAX_TOKENS": "many",
            },
            clear=False,
        ):
            settings = get_settings()

        self.assertEqual(settings.temperature, 0.7)
        self.assertEqual(settings.max_tokens, 1024)

    def test_settings_have_required_defaults(self):
        settings = get_settings()

        self.assertTrue(settings.base_url)
        self.assertTrue(settings.model_name)
        self.assertIn(settings.embedding_mode, {"api", "local"})


if __name__ == "__main__":
    unittest.main()
