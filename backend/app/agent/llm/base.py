from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments_json: str


@dataclass
class ChatTurn:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


# OpenAI-style message dicts: role, content, tool_calls, tool_call_id, name
ChatMessageDict = dict
