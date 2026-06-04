import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.config import get_settings
from src.llm_client import ChatResult, chat_completion


class LlmClientTests(unittest.TestCase):
    def test_chat_completion_returns_error_without_api_key(self):
        with patch.dict(os.environ, {"API_KEY": "your_api_key_here"}, clear=False):
            result = chat_completion("sys", "hello", settings=get_settings())

        self.assertIsInstance(result, ChatResult)
        self.assertFalse(result.success)
        self.assertIn("API Key", result.error)

    def test_chat_completion_handles_mocked_successful_response(self):
        class FakeCompletions:
            def create(self, **kwargs):
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
                    usage=SimpleNamespace(prompt_tokens=5, completion_tokens=2),
                )

        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=FakeCompletions())
        )

        with patch("src.llm_client._build_client", return_value=fake_client):
            with patch.dict(os.environ, {"API_KEY": "sk-test"}, clear=False):
                result = chat_completion("sys", "hello", settings=get_settings())

        self.assertTrue(result.success)
        self.assertEqual(result.content, "ok")
        self.assertEqual(result.input_tokens, 5)
        self.assertEqual(result.output_tokens, 2)


if __name__ == "__main__":
    unittest.main()
