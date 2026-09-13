import json
from collections.abc import AsyncIterator

from app.agent.llm.factory import get_llm
from app.agent.prompts import SYSTEM_PROMPT
from app.config import get_settings
from app.tools import registry


def _build_openai_messages(history: list[dict], message: str) -> list[dict]:
    msgs: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            msgs.append({"role": m["role"], "content": m["content"]})
    if message.strip():
        last = msgs[-1] if msgs else None
        if not (last and last.get("role") == "user" and last.get("content") == message.strip()):
            msgs.append({"role": "user", "content": message.strip()})
    return msgs


async def stream_agent_sse(session_id: str, history: list[dict], message: str) -> AsyncIterator[str]:
    settings = get_settings()
    llm = get_llm(settings)
    messages = _build_openai_messages(history, message)
    final_text = ""

    for _ in range(settings.max_tool_iterations):
        turn = await llm.chat_with_tools(messages, registry.TOOLS)
        if not turn.tool_calls:
            final_text = (turn.content or "").strip()
            break
        llm.append_assistant_tool_turn(messages, turn)
        for tc in turn.tool_calls:
            args = json.loads(tc.arguments_json or "{}")
            result = registry.execute_tool(session_id, tc.name, args)
            llm.append_tool_result(messages, tc.id, tc.name, result)

    if final_text:
        for ch in final_text:
            yield ch
        return

    async for piece in llm.stream_chat(messages):
        yield piece
