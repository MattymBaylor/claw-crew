"""Thin wrapper around the Anthropic SDK used by every agent to think."""

from __future__ import annotations

import os


class ClaudeClient:
    def __init__(
        self,
        model: str,
        max_tokens: int = 1024,
        api_key: str | None = None,
    ) -> None:
        # Imported lazily so config/provision tooling works without the SDK.
        from anthropic import Anthropic

        self.model = model
        self.max_tokens = max_tokens
        self._client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def reply(self, system_prompt: str, user_text: str) -> str:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_text}],
        )
        parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
        return "\n".join(parts).strip() or "(no response)"
