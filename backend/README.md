# AI Purchasing Agent — Backend

FastAPI service: chat API, Gemini tool loop, JSON buyer store.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# source .venv/Scripts/activate    # Windows
pip install -r requirements.txt
cp .env.example .env
# Set GEMINI_API_KEY in .env
```

If [`app/data/buyers.json`](app/data/buyers.json) is missing, it is copied from [`app/data/seed/buyers.json`](app/data/seed/buyers.json).

## Run

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend: `cd ../frontend && npm install && npm run dev` (proxies `/api` to `:8000`).

## Code map

| File | Role |
|------|------|
| [`app/agent/prompts.py`](app/agent/prompts.py) | System prompt |
| [`app/agent/runner.py`](app/agent/runner.py) | Gemini tool loop, SSE reply |
| [`app/agent/llm/gemini_client.py`](app/agent/llm/gemini_client.py) | Gemini API |
| [`app/tools/registry.py`](app/tools/registry.py) | Tool schemas and dispatch |
| [`app/tools/read.py`](app/tools/read.py) | Read ERP data |
| [`app/tools/actions.py`](app/tools/actions.py) | PO create/modify/validate, planning |
| [`app/tools/store.py`](app/tools/store.py) | Load/save `buyers.json` |
| [`app/api/chat.py`](app/api/chat.py) | `POST /api/chat` |
| [`app/api/conversations.py`](app/api/conversations.py) | Saved chats |

## Data

- **Seed:** `app/data/seed/buyers.json` (initial state, in git)
- **Live:** `app/data/buyers.json` (PO writes persist here; gitignored)
- Reset: copy seed over live file
- Purchase **recommendations** come from the user message in chat, not from JSON

`app/tools/store.py` loads and saves the live file; `read.py` and `actions.py` are the tool wrappers that read/write through the store (see root [README](../README.md) — *Mocking external services and databases*).

Default buyer id for tools: `BUYER-01`.

## Environment

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Required |
| `GEMINI_MODEL` | Default `gemini-3.5-flash-lite` |
| `MAX_TOOL_ITERATIONS` | Tool rounds before stop (default `10`) |

## Tests

```bash
pytest
```

See [`tests/conftest.py`](tests/conftest.py) for isolated buyer data.

## HTTP API

- OpenAPI spec: [`openapi.yaml`](openapi.yaml)
- Example requests: [`api-collection/`](api-collection/)

Past chats: **New chat** → `POST /api/conversations`. List/get: `GET /api/conversations`, `GET /api/conversations/{id}`. Saved files live in `app/data/conversations/` (see root README — *Test scenarios and evaluation approach*).
