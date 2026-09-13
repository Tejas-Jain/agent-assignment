import base64

from app.agent.llm.base import ChatTurn, ToolCall
from app.agent.llm.gemini_client import GeminiClient
from app.config import Settings


def test_assistant_tool_turn_roundtrips_thought_signature():
    client = GeminiClient(Settings(gemini_api_key="test-key"))
    sig = b"gemini-thought-sig-bytes"
    messages: list[dict] = []
    client.append_assistant_tool_turn(
        messages,
        ChatTurn(
            tool_calls=[
                ToolCall(
                    id="call_get_purchase_recommendation_0",
                    name="get_purchase_recommendation",
                    arguments_json="{}",
                    thought_signature_b64=base64.b64encode(sig).decode("ascii"),
                )
            ]
        ),
    )
    contents = client._to_gemini_contents(messages)
    assert len(contents) == 1
    part = contents[0].parts[0]
    assert part.function_call.name == "get_purchase_recommendation"
    assert part.thought_signature == sig
