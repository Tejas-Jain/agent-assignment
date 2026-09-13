import base64

from app.agent.llm.base import LLMResponse, Message, ToolCall, append_assistant_tool_turn
from app.agent.llm.gemini_client import GeminiProvider
from app.config import Settings


def test_assistant_tool_turn_roundtrips_thought_signature():
    provider = GeminiProvider(Settings(gemini_api_key="test-key"))
    sig = b"gemini-thought-sig-bytes"
    messages: list[Message] = []
    append_assistant_tool_turn(
        messages,
        LLMResponse(
            tool_calls=[
                ToolCall(
                    id="call_get_inventory_0",
                    name="get_inventory",
                    arguments_json='{"sku": "PROD-001"}',
                    thought_signature_b64=base64.b64encode(sig).decode("ascii"),
                )
            ]
        ),
    )
    contents = provider._to_gemini_contents(messages)
    assert len(contents) == 1
    part = contents[0].parts[0]
    assert part.function_call.name == "get_inventory"
    assert part.thought_signature == sig
