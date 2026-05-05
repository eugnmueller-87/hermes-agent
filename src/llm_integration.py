"""LLM API integration — wraps Anthropic Claude for content generation."""

import os
import anthropic

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"


class LLMClient:
    def __init__(self, api_key: str = None):
        self._client = anthropic.Anthropic(
            api_key=api_key or os.environ["ANTHROPIC_API_KEY"]
        )

    def generate(
        self,
        prompt: str,
        system: str = None,
        model: str = SONNET,
        max_tokens: int = 1024,
    ) -> str:
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)
        return next(
            (block.text for block in response.content if hasattr(block, "text")),
            "",
        )

    def generate_linkedin_post(self, prompt: str) -> str:
        return self.generate(prompt, model=SONNET, max_tokens=600)

    def generate_brief(self, prompt: str) -> str:
        return self.generate(prompt, model=HAIKU, max_tokens=300)

    def classify_signal(self, prompt: str) -> str:
        return self.generate(prompt, model=HAIKU, max_tokens=100)
