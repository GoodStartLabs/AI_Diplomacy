import os
import unittest

from lm_service_versus import (
    OpenAIClient, 
    ClaudeClient, 
    GeminiClient, 
    DeepSeekClient
)

class TestOpenAIClient(unittest.TestCase):
    def setUp(self):
        self.model_name = "gpt-4o-mini"  # or "o3-mini", etc.
        self.client = OpenAIClient(self.model_name)

    def test_openai_key_exists(self):
        self.assertIsNotNone(os.environ.get("OPENAI_API_KEY"), 
            "OPENAI_API_KEY is not set in the environment.")

    def test_openai_basic_response(self):
        """Integration test: calls the LLM with a minimal prompt."""
        prompt = "Hello from unit test. Please respond with a short phrase."
        response = self.client.generate_response(prompt)
        self.assertTrue(len(response) > 0, "OpenAI returned an empty response.")


class TestClaudeClient(unittest.TestCase):
    def setUp(self):
        self.model_name = "claude-3-5-sonnet-20241022"  # or "claude-3-5-sonnet-20241022"
        self.client = ClaudeClient(self.model_name)

    def test_claude_key_exists(self):
        self.assertIsNotNone(os.environ.get("ANTHROPIC_API_KEY"), 
            "ANTHROPIC_API_KEY is not set in the environment.")

    def test_claude_basic_response(self):
        prompt = "Hello from unit test. Please respond with a short phrase."
        response = self.client.generate_response(prompt)
        self.assertTrue(len(response) > 0, "Claude returned an empty response.")


class TestGeminiClient(unittest.TestCase):
    def setUp(self):
        self.model_name = "gemini-1.5-flash"
        self.client = GeminiClient(self.model_name)

    def test_gemini_key_exists(self):
        self.assertIsNotNone(os.environ.get("GEMINI_API_KEY"), 
            "GEMINI_API_KEY is not set in the environment.")

    def test_gemini_basic_response(self):
        prompt = "Hello from unit test. Please respond with a short phrase."
        response = self.client.generate_response(prompt)
        self.assertTrue(len(response) > 0, "Gemini returned an empty response.")


class TestDeepSeekClient(unittest.TestCase):
    def setUp(self):
        self.model_name = "deepseek-reasoner"
        self.client = DeepSeekClient(self.model_name)

    def test_deepseek_key_exists(self):
        self.assertIsNotNone(os.environ.get("DEEPSEEK_API_KEY"), 
            "DEEPSEEK_API_KEY is not set in the environment.")

    def test_deepseek_basic_response(self):
        prompt = "Hello from unit test. Please respond with a short phrase."
        response = self.client.generate_response(prompt)
        self.assertTrue(len(response) > 0, "DeepSeek returned an empty response.")


if __name__ == '__main__':
    unittest.main() 