import json
from collections.abc import AsyncIterator

from app.agent.llm.base import LLMRequest, Message, append_assistant_tool_turn, append_tool_result
from app.agent.llm.gemini_client import GeminiProvider
from app.agent.prompts import SYSTEM_PROMPT
from app.config import get_settings
from app.tools import registry


def _build_llm_messages(history: list[dict], message: str) -> list[Message]:
    msgs: list[Message] = [Message(role="system", content=SYSTEM_PROMPT)]
    for m in history:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            msgs.append(Message(role=m["role"], content=m["content"]))
    if message.strip():
        last = msgs[-1] if msgs else None
        if not (last and last.role == "user" and last.content == message.strip()):
            msgs.append(Message(role="user", content=message.strip()))
    return msgs


async def stream_agent_sse(session_id: str, history: list[dict], message: str) -> AsyncIterator[str]:
    settings = get_settings()
    llm = GeminiProvider(settings)
    messages = _build_llm_messages(history, message)
    final_text = ""

    for _ in range(settings.max_tool_iterations):
        turn = await llm.generate(LLMRequest(messages=messages, tools=registry.TOOLS))
        if not turn.tool_calls:
            final_text = (turn.content or "").strip()
            break
        append_assistant_tool_turn(messages, turn)
        for tc in turn.tool_calls:
            args = json.loads(tc.arguments_json or "{}")
            result = registry.execute_tool(session_id, tc.name, args)
            append_tool_result(messages, tc.id, tc.name, result)
    else:
        final_text = (
            f"Agent stopped after {settings.max_tool_iterations} tool rounds without a final reply. "
            "Try a shorter question or increase max_tool_iterations."
        )

    if final_text:
        yield final_text
