# 5AI Web

A web version of the original PySide6 desktop app. `backend.py` is copied
over **unchanged** (same `Database`, `stream_chat`, models). The PySide6 UI
(`ui.py`) has been replaced with:

- `server.py` — FastAPI app exposing login/register/chat routes, streams
  AI replies over Server-Sent Events (SSE) instead of Qt signals.
- `templates/login.html`, `templates/chat.html` — page structure (Jinja2).
- `static/style.css` — theme ported from `Theme.DARK` / `apply_theme()`.
- `static/app.js` — sending messages, streaming into the page, sidebar
  interactions, auto-growing textarea (mirrors `GrowingTextEdit`).

## Run locally

```bash
cd webapp
pip install -r requirements.txt
uvicorn server:app --reload
```

Open http://127.0.0.1:8000

## IMPORTANT before deploying anywhere public

`backend.py` has a **hardcoded Groq API key**. Rotate it on Groq's
dashboard and load it from an environment variable instead, e.g.:

```python
import os
API_KEY = os.environ.get("GROQ_API_KEY")
```

Then set `GROQ_API_KEY` in Render's environment variable settings
(never commit it to the repo).

## Notes on deploying to Render

- Storage (`users_db.json`, `chats/`, `model_prefs.json`, etc.) is plain
  JSON on local disk, same as the desktop app. Render's default
  filesystem is **ephemeral** — files vanish on redeploy/restart. Either:
  - attach a Render **persistent disk**, or
  - migrate `Database` to Postgres (Render offers a free/managed
    Postgres instance) for anything you care about keeping.
- Start command for Render: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- This has **not been tested** — it was generated as a structural port of
  the existing desktop app and should be run/debugged locally before
  deploying.
