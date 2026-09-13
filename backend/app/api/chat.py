import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.agent.runner import stream_agent_sse
from app.models.chat import ChatRequest
from app.sse import sse_event

router = APIRouter()


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    history = [m.model_dump() for m in body.messages]

    async def event_stream():
        try:
            async for chunk in stream_agent_sse(history, body.message):
                yield sse_event({"type": "token", "content": chunk})
            yield sse_event({"type": "done"})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            yield sse_event({"type": "error", "content": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
