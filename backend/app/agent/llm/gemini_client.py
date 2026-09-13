import asyncio
import base64
import json
from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import types

from app.agent.llm.base import LLMProvider, LLMRequest, LLMResponse, Message, ToolCall, ToolDefinition
from app.config import Settings


class GeminiProvider(LLMProvider):
    def __init__(self, settings: Settings):
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    def _to_gemini_declarations(self, tools: list[ToolDefinition]) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters or {"type": "object", "properties": {}}}
            for t in tools
        ]

    def _to_gemini_contents(self, messages: list[Message]) -> list[types.Content]:
        contents: list[types.Content] = []
        for msg in messages:
            if msg.role == "system":
                contents.append(types.Content(role="user", parts=[types.Part(text=f"[System]\n{msg.content}")]))
                contents.append(types.Content(role="model", parts=[types.Part(text="Understood.")]))
            elif msg.role == "user":
                contents.append(types.Content(role="user", parts=[types.Part(text=msg.content or "")]))
            elif msg.role == "assistant":
                parts: list[types.Part] = []
                if msg.content:
                    parts.append(types.Part(text=msg.content))
                for tc in msg.tool_calls:
                    part_kwargs: dict[str, Any] = {
                        "function_call": types.FunctionCall(
                            name=tc.name,
                            args=json.loads(tc.arguments_json or "{}"),
                        )
                    }
                    if tc.thought_signature_b64:
                        part_kwargs["thought_signature"] = base64.b64decode(tc.thought_signature_b64)
                    parts.append(types.Part(**part_kwargs))
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
            elif msg.role == "tool":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=msg.name or "tool",
                                    response={"result": json.loads(msg.content) if msg.content else {}},
                                )
                            )
                        ],
                    )
                )
        return contents

    async def generate(self, request: LLMRequest) -> LLMResponse:
        declarations = self._to_gemini_declarations(request.tools)
        tool_config = types.Tool(function_declarations=[types.FunctionDeclaration(**d) for d in declarations])
        contents = self._to_gemini_contents(request.messages)
        config = types.GenerateContentConfig(tools=[tool_config]) if declarations else None

        def _call():
            return self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
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
                    sig_b64 = base64.b64encode(part.thought_signature).decode("ascii") if part.thought_signature else None
                    tool_calls.append(
                        ToolCall(
                            id=f"call_{fc.name}_{len(tool_calls)}",
                            name=fc.name,
                            arguments_json=json.dumps(args),
                            thought_signature_b64=sig_b64,
                        )
                    )
        return LLMResponse(content="".join(text_parts) or None, tool_calls=tool_calls)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        contents = self._to_gemini_contents(request.messages)

        def _call():
            return self._client.models.generate_content_stream(model=self._model, contents=contents)

        stream = await asyncio.to_thread(_call)
        for chunk in stream:
            if chunk.text:
                yield chunk.text
