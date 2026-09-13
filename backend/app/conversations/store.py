import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import Settings, get_settings
from app.models.conversation import PastConversation, PastConversationSummary

_SAFE_ID = re.compile(r"^[\w-]+$")


def _conversations_dir(settings: Settings | None = None) -> Path:
    s = settings or get_settings()
    if s.conversations_dir.strip():
        return Path(s.conversations_dir)
    return Path(__file__).resolve().parent.parent / "data" / "conversations"


def _title_from_messages(messages: list[dict]) -> str:
    for msg in messages:
        if msg.get("role") == "user" and (msg.get("content") or "").strip():
            text = msg["content"].strip().replace("\n", " ")
            return text[:80] + ("…" if len(text) > 80 else "")
    return "Conversation"


def save_conversation(messages: list[dict], settings: Settings | None = None) -> PastConversation:
    directory = _conversations_dir(settings)
    directory.mkdir(parents=True, exist_ok=True)
    conv_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
    doc = {
        "id": conv_id,
        "title": _title_from_messages(messages),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": messages,
    }
    (directory / f"{conv_id}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    return PastConversation.model_validate(doc)


def list_conversations(settings: Settings | None = None) -> list[PastConversationSummary]:
    directory = _conversations_dir(settings)
    if not directory.is_dir():
        return []
    summaries: list[PastConversationSummary] = []
    for path in directory.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            summaries.append(PastConversationSummary(id=data["id"], title=data["title"], created_at=data["created_at"]))
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    summaries.sort(key=lambda s: s.created_at, reverse=True)
    return summaries


def get_conversation(conversation_id: str, settings: Settings | None = None) -> PastConversation | None:
    if not _SAFE_ID.match(conversation_id):
        return None
    path = _conversations_dir(settings) / f"{conversation_id}.json"
    if not path.is_file():
        return None
    try:
        return PastConversation.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValueError):
        return None
