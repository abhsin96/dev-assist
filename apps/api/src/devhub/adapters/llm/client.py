from __future__ import annotations


class AnthropicLLMClient:
    """Stub LLM client — full implementation in DEVHUB-011."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def is_healthy(self) -> bool:
        return bool(self._api_key)
