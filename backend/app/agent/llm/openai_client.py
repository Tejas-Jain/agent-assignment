import json
from typing import Any

from openai import AsyncOpenAI

from app.agent.llm.base import ChatTurn, ToolCall
from app.config import Settings


class OpenAIClient:
    def __init__(self, settings: Settings):
        kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = settings.openai_model

    async def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> ChatTurn:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        choice = response.choices[0].message
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments_json=tc.function.arguments or "{}")
            for tc in (choice.tool_calls or [])
        ]
        return ChatTurn(content=choice.content, tool_calls=tool_calls)

    async def stream_chat(self, messages: list[dict]):
        stream = await self._client.chat.completions.create(model=self._model, messages=messages, stream=True)
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def append_assistant_tool_turn(self, messages: list[dict], turn: ChatTurn) -> None:
        messages.append(
            {
                "role": "assistant",
                "content": turn.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments_json},
                    }
                    for tc in turn.tool_calls
                ],
            }
        )

    def append_tool_result(self, messages: list[dict], tool_call_id: str, name: str, result: str) -> None:
        messages.append({"role": "tool", "tool_call_id": tool_call_id, "name": name, "content": result})
