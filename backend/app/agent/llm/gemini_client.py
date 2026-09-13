import asyncio
import json
from typing import Any

from google import genai
from google.genai import types

from app.agent.llm.base import ChatTurn, ToolCall
from app.agent.llm.schema_map import openai_tools_to_gemini_declarations
from app.config import Settings


class GeminiClient:
    def __init__(self, settings: Settings):
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    def _to_gemini_contents(self, messages: list[dict]) -> list[types.Content]:
        contents: list[types.Content] = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                contents.append(types.Content(role="user", parts=[types.Part(text=f"[System]\n{msg['content']}")]))
                contents.append(types.Content(role="model", parts=[types.Part(text="Understood.")]))
            elif role == "user":
                contents.append(types.Content(role="user", parts=[types.Part(text=msg["content"] or "")]))
            elif role == "assistant":
                parts: list[types.Part] = []
                if msg.get("content"):
                    parts.append(types.Part(text=msg["content"]))
                for tc in msg.get("tool_calls") or []:
                    fn = tc["function"]
                    parts.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                name=fn["name"],
                                args=json.loads(fn.get("arguments") or "{}"),
                            )
                        )
                    )
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
            elif role == "tool":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=msg.get("name") or "tool",
                                    response={"result": json.loads(msg["content"]) if msg.get("content") else {}},
                                )
                            )
                        ],
                    )
                )
        return contents

    async def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> ChatTurn:
        declarations = openai_tools_to_gemini_declarations(tools)
        tool_config = types.Tool(function_declarations=[types.FunctionDeclaration(**d) for d in declarations])
        contents = self._to_gemini_contents(messages)

        def _call():
            return self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(tools=[tool_config]),
            )

        response = await asyncio.to_thread(_call)
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                if part.text:
                    text_parts.append(part.text)
                if part.function_call:
                    fc = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    tool_calls.append(
                        ToolCall(
                            id=f"call_{fc.name}_{len(tool_calls)}",
                            name=fc.name,
                            arguments_json=json.dumps(args),
                        )
                    )
        return ChatTurn(content="".join(text_parts) or None, tool_calls=tool_calls)

    async def stream_chat(self, messages: list[dict]):
        contents = self._to_gemini_contents(messages)

        def _call():
            return self._client.models.generate_content_stream(model=self._model, contents=contents)

        stream = await asyncio.to_thread(_call)
        for chunk in stream:
            if chunk.text:
                yield chunk.text

    def append_assistant_tool_turn(self, messages: list[dict], turn: ChatTurn) -> None:
        messages.append(
            {
                "role": "assistant",
                "content": turn.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.arguments_json}}
                    for tc in turn.tool_calls
                ],
            }
        )

    def append_tool_result(self, messages: list[dict], tool_call_id: str, name: str, result: str) -> None:
        messages.append({"role": "tool", "tool_call_id": tool_call_id, "name": name, "content": result})
