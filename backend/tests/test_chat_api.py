from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main.validate_settings"):
            resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_sse_done_event():
    async def fake_stream(*_args, **_kwargs):
        yield "Decision: investigate further."
        yield " Key factors listed."

    with patch("app.api.chat.stream_agent_sse", fake_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/api/chat",
                json={"message": "Review the 1000 unit recommendation", "messages": []},
                headers={"Accept": "text/event-stream"},
            ) as resp:
                assert resp.status_code == 200
                body = ""
                async for chunk in resp.aiter_text():
                    body += chunk
    assert '"type": "done"' in body or '"type":"done"' in body.replace(" ", "")
