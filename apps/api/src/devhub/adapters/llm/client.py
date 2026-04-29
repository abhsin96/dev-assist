from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage


class AnthropicLLMClient:
    """LLM adapter backed by Claude via langchain-anthropic."""

    _MODEL = "claude-opus-4-7"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = ChatAnthropic(  # type: ignore[call-arg]
            model=self._MODEL,
            api_key=api_key,  # type: ignore[arg-type]
        )

    async def is_healthy(self) -> bool:
        return bool(self._api_key)

    async def chat(
        self,
        messages: list[BaseMessage],
        *,
        system: str | None = None,
    ) -> AIMessage:
        all_messages: list[BaseMessage] = []
        if system:
            all_messages.append(SystemMessage(content=system))
        all_messages.extend(messages)
        result = await self._client.ainvoke(all_messages)
        return AIMessage(content=str(result.content))
