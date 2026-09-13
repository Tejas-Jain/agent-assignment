from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ToolCall:
    id: str
    name: str
    arguments_json: str
    thought_signature_b64: str | None = None


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


ChatTurn = LLMResponse


MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: MessageRole
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict


@dataclass
class LLMRequest:
    messages: list[Message]
    tools: list[ToolDefinition] = field(default_factory=list)


def append_assistant_tool_turn(messages: list[Message], turn: LLMResponse) -> None:
    messages.append(
        Message(
            role="assistant",
            content=turn.content,
            tool_calls=list(turn.tool_calls),
        )
    )


def append_tool_result(messages: list[Message], tool_call_id: str, name: str, result: str) -> None:
    messages.append(Message(role="tool", tool_call_id=tool_call_id, name=name, content=result))


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        pass

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        pass
