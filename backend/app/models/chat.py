from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str = ""


class ChatRequest(BaseModel):
    message: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)
