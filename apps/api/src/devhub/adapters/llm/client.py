from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


class AnthropicLLMClient:
    """LLM adapter backed by Claude via langchain-anthropic."""

    _MODEL = "claude-opus-4-7"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = ChatAnthropic(
            model_name=self._MODEL,
            api_key=SecretStr(api_key),
            timeout=None,
            stop=None,
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


class OpenAILLMClient:
    """LLM adapter backed by OpenAI via langchain-openai."""

    _MODEL = "gpt-4o"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = ChatOpenAI(
            model=self._MODEL,
            api_key=SecretStr(api_key),
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
