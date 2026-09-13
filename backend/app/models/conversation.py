from pydantic import BaseModel, Field

from app.models.chat import ChatMessage


class PastConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str


class PastConversation(BaseModel):
    id: str
    title: str
    created_at: str
    messages: list[ChatMessage] = Field(default_factory=list)


class SaveConversationRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
