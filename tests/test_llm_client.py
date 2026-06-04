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

    def test_chat_completion_uses_settings_generation_params(self):
        class FakeCompletions:
            def __init__(self):
                self.last_kwargs = {}

            def create(self, **kwargs):
                self.last_kwargs = kwargs
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
                    usage=SimpleNamespace(prompt_tokens=5, completion_tokens=2),
                )

        fake_completions = FakeCompletions()
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=fake_completions)
        )

        with patch("src.llm_client._build_client", return_value=fake_client):
            with patch.dict(
                os.environ,
                {
                    "API_KEY": "sk-test",
                    "DEFAULT_TEMPERATURE": "0.9",
                    "DEFAULT_MAX_TOKENS": "2048",
                },
                clear=False,
            ):
                from src.config import get_settings

                settings = get_settings()
                result = chat_completion("sys", "hello", settings=settings)

        self.assertTrue(result.success)
        self.assertEqual(fake_completions.last_kwargs["temperature"], 0.9)
        self.assertEqual(fake_completions.last_kwargs["max_tokens"], 2048)


if __name__ == "__main__":
    unittest.main()
