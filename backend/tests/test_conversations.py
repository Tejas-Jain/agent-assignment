from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.conversations import store
from app.main import app


@pytest.fixture
def conversations_tmp(tmp_path, monkeypatch):
    conv_dir = tmp_path / "conversations"
    conv_dir.mkdir()
    monkeypatch.setenv("CONVERSATIONS_DIR", str(conv_dir))
    from app.config import get_settings

    get_settings.cache_clear()
    yield conv_dir
    get_settings.cache_clear()


def test_save_and_list_conversations(conversations_tmp):
    store.save_conversation(
        [
            {"role": "user", "content": "Review the 1000 unit recommendation"},
            {"role": "assistant", "content": "Decision: investigate further."},
        ]
    )
    items = store.list_conversations()
    assert len(items) == 1
    assert "1000" in items[0].title
    full = store.get_conversation(items[0].id)
    assert full is not None
    assert len(full.messages) == 2


@pytest.mark.asyncio
async def test_list_conversations_api(conversations_tmp):
    store.save_conversation([{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main.validate_settings"):
            resp = await client.get("/api/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"]


@pytest.mark.asyncio
async def test_get_conversation_api(conversations_tmp):
    saved = store.save_conversation([{"role": "user", "content": "Q"}, {"role": "assistant", "content": "A"}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main.validate_settings"):
            resp = await client.get(f"/api/conversations/{saved.id}")
            missing = await client.get("/api/conversations/does-not-exist")
    assert resp.status_code == 200
    assert resp.json()["messages"][1]["content"] == "A"
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_post_conversation_api(conversations_tmp):
    payload = {
        "messages": [
            {"role": "user", "content": "Review PO"},
            {"role": "assistant", "content": "Decision: accept."},
        ]
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main.validate_settings"):
            resp = await client.post("/api/conversations", json=payload)
    assert resp.status_code == 201
    assert resp.json()["id"]
    assert len(list(conversations_tmp.glob("*.json"))) == 1


@pytest.mark.asyncio
async def test_chat_does_not_auto_save(conversations_tmp):
    async def fake_stream(*_args, **_kwargs):
        yield "Done."

    with patch("app.api.chat.stream_agent_sse", fake_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.main.validate_settings"):
                async with client.stream(
                    "POST",
                    "/api/chat",
                    json={"message": "Review PO", "messages": []},
                    headers={"Accept": "text/event-stream"},
                ) as resp:
                    async for _chunk in resp.aiter_text():
                        pass
    assert len(list(conversations_tmp.glob("*.json"))) == 0
