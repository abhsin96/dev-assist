from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage


class AnthropicLLMClient:
    """LLM adapter — full streaming impl in DEVHUB-011.

    Currently returns a stub routing response so the supervisor graph runs
    in dev/test without an Anthropic key.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def is_healthy(self) -> bool:
        return bool(self._api_key)

    async def chat(
        self,
        messages: list[BaseMessage],
        *,
        system: str | None = None,
    ) -> AIMessage:
        # Stub: always route to echo_specialist once, then DONE.
        has_echo_reply = any(
            isinstance(m, AIMessage)
            and isinstance(m.content, str)
            and m.content.startswith("[echo]")
            for m in messages
        )
        if has_echo_reply:
            return AIMessage(content='{"route": "DONE", "reasoning": "echo complete"}')
        return AIMessage(content='{"route": "echo_specialist", "reasoning": "delegating to echo"}')
