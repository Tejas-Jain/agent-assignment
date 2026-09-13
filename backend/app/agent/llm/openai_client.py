from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.agent.llm.base import LLMProvider, LLMRequest, LLMResponse, Message, ToolCall, ToolDefinition
from app.config import Settings


class OpenAIProvider(LLMProvider):
    def __init__(self, settings: Settings):
        kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = settings.openai_model

    def _to_openai_messages(self, messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        for msg in messages:
            if msg.role == "assistant":
                out.append(
                    {
                        "role": "assistant",
                        "content": msg.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.name, "arguments": tc.arguments_json},
                            }
                            for tc in msg.tool_calls
                        ],
                    }
                )
            elif msg.role == "tool":
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id,
                        "name": msg.name,
                        "content": msg.content,
                    }
                )
            else:
                out.append({"role": msg.role, "content": msg.content})
        return out

    def _to_openai_tools(self, tools: list[ToolDefinition]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
            }
            for t in tools
        ]

    async def generate(self, request: LLMRequest) -> LLMResponse:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=self._to_openai_messages(request.messages),
            tools=self._to_openai_tools(request.tools),
            tool_choice="auto",
        )
        choice = response.choices[0].message
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments_json=tc.function.arguments or "{}")
            for tc in (choice.tool_calls or [])
        ]
        return LLMResponse(content=choice.content, tool_calls=tool_calls)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=self._to_openai_messages(request.messages),
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
