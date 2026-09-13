import copy
import json
from pathlib import Path

_FIXTURE_PATH = Path(__file__).resolve().parent.parent / "data" / "scenario1.json"
_BASE = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
_sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = copy.deepcopy(_BASE)
    return _sessions[session_id]


def reset_session(session_id: str) -> None:
    _sessions[session_id] = copy.deepcopy(_BASE)
