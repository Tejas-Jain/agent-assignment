from fastapi import APIRouter, HTTPException

from app.conversations import store
from app.models.conversation import PastConversation, PastConversationSummary, SaveConversationRequest

router = APIRouter()


@router.post("/conversations", response_model=PastConversation, status_code=201)
def save_past_conversation(body: SaveConversationRequest):
    messages = [m.model_dump() for m in body.messages]
    return store.save_conversation(messages)


@router.get("/conversations", response_model=list[PastConversationSummary])
def list_past_conversations():
    return store.list_conversations()


@router.get("/conversations/{conversation_id}", response_model=PastConversation)
def get_past_conversation(conversation_id: str):
    conversation = store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
