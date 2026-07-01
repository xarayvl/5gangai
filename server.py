#!/usr/bin/env python3
"""
server.py - 5AI Web Backend (FastAPI)
======================================
Wraps the existing backend.py (Database, stream_chat, models) with a
web server instead of the PySide6 desktop UI.

Run locally with:
    pip install -r requirements.txt
    uvicorn server:app --reload

Then open http://127.0.0.1:8000
"""

import json
from pathlib import Path

from fastapi import FastAPI, Request, Response, Cookie
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend import (
    Database,
    stream_chat,
    SYSTEM_PROMPT,
    AVAILABLE_MODELS,
    MODEL,
    MAX_CHATS_PER_USER,
    model_display_name,
)
import i18n

BASE_DIR = Path(__file__).parent.resolve()

app = FastAPI(title="5AI Web")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ============================================================
#                     SESSION HELPERS
# ============================================================
# Very lightweight "session": the logged-in username is stored in a
# plain cookie. This mirrors the simplicity of the original desktop
# app (plaintext users_db.json) - for real production use, swap this
# for signed/secure sessions.

def get_current_user(session_user: str | None) -> str | None:
    if not session_user:
        return None
    users = Database.load_users()
    if session_user in users:
        return session_user
    return None


# ============================================================
#                          PAGES
# ============================================================
@app.get("/", response_class=HTMLResponse)
def index(request: Request, session_user: str | None = Cookie(default=None)):
    user = get_current_user(session_user)
    if not user:
        return RedirectResponse(url="/login")
    return RedirectResponse(url="/chat")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, session_user: str | None = Cookie(default=None)):
    if get_current_user(session_user):
        return RedirectResponse(url="/chat")

    remembered = Database.load_remember()
    # No one is logged in yet on this screen, so there's no username to
    # key a preference by. Fall back to a per-browser cookie (set once
    # the visitor logs in and their real preference is known) instead
    # of a global file, so this page doesn't inherit whatever language
    # the last person to log in on this deployment happened to pick.
    current_language = request.cookies.get("ui_lang", "en")
    strings = i18n.get_translations(current_language)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "remembered": remembered,
            "error": None,
            "mode": "login",
            "current_language": current_language,
            "t": i18n.translator(current_language),
            "i18n_json": json.dumps(strings, ensure_ascii=False),
        },
    )


@app.post("/login")
def login_submit(request: Request, response: Response):
    return JSONResponse({"detail": "Use /api/login (POST JSON) instead."}, status_code=400)


@app.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request, session_user: str | None = Cookie(default=None)):
    user = get_current_user(session_user)
    if not user:
        return RedirectResponse(url="/login")

    chats = Database.list_chats(user)
    current_model = Database.load_model(user)
    current_language = Database.load_language(user)

    if chats:
        current_chat_id = chats[0]["id"]
        messages = Database.load_chat(user, current_chat_id)
    else:
        current_chat_id = Database.new_chat_id()
        messages = [dict(SYSTEM_PROMPT)]

    # Only show user/assistant turns in the UI (hide system prompt)
    visible_messages = [m for m in messages if m.get("role") in ("user", "assistant")]

    strings = i18n.get_translations(current_language)

    return templates.TemplateResponse(
        request,
        "chat.html",
        {
            "username": user,
            "chats": chats,
            "current_chat_id": current_chat_id,
            "messages": visible_messages,
            "models": AVAILABLE_MODELS,
            "current_model": current_model,
            "current_model_name": model_display_name(current_model),
            "current_language": current_language,
            "t": i18n.translator(current_language),
            "i18n_json": json.dumps(strings, ensure_ascii=False),
            "max_chats": MAX_CHATS_PER_USER,
        },
    )


# ============================================================
#                       AUTH API
# ============================================================
@app.post("/api/login")
async def api_login(request: Request):
    data = await request.json()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    remember = bool(data.get("remember"))

    if not Database.login(username, password):
        return JSONResponse({"ok": False, "error": "Invalid username or password."}, status_code=401)

    if remember:
        Database.save_remember(username)
    else:
        Database.clear_remember()

    resp = JSONResponse({"ok": True})
    # 30 day cookie if remembered, session cookie otherwise
    max_age = 60 * 60 * 24 * 30 if remember else None
    resp.set_cookie("session_user", username, max_age=max_age, httponly=True, samesite="lax")
    return resp


@app.post("/api/register")
async def api_register(request: Request):
    data = await request.json()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return JSONResponse({"ok": False, "error": "Username and password required."}, status_code=400)

    ok, msg = Database.register(username, password)
    if not ok:
        return JSONResponse({"ok": False, "error": msg}, status_code=400)
    return JSONResponse({"ok": True, "message": msg})


@app.post("/api/logout")
def api_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("session_user")
    return resp


# ============================================================
#                       CHAT API
# ============================================================
@app.get("/api/chats")
def api_list_chats(session_user: str | None = Cookie(default=None)):
    user = get_current_user(session_user)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in."}, status_code=401)
    return {"ok": True, "chats": Database.list_chats(user)}


@app.get("/api/chats/{chat_id}")
def api_load_chat(chat_id: str, session_user: str | None = Cookie(default=None)):
    user = get_current_user(session_user)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in."}, status_code=401)
    messages = Database.load_chat(user, chat_id)
    visible = [m for m in messages if m.get("role") in ("user", "assistant")]
    return {"ok": True, "messages": visible}


@app.post("/api/chats/new")
def api_new_chat(session_user: str | None = Cookie(default=None)):
    user = get_current_user(session_user)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in."}, status_code=401)

    if Database.count_chats(user) >= MAX_CHATS_PER_USER:
        lang = Database.load_language(user)
        msg = i18n.translator(lang)("chat_limit_reached")
        return JSONResponse({"ok": False, "error": msg, "limit_reached": True}, status_code=400)

    chat_id = Database.new_chat_id()
    return {"ok": True, "chat_id": chat_id}


@app.delete("/api/chats/{chat_id}")
def api_delete_chat(chat_id: str, session_user: str | None = Cookie(default=None)):
    user = get_current_user(session_user)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in."}, status_code=401)
    Database.delete_chat(user, chat_id)
    return {"ok": True}


@app.post("/api/model")
async def api_set_model(request: Request, session_user: str | None = Cookie(default=None)):
    user = get_current_user(session_user)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in."}, status_code=401)
    data = await request.json()
    model_id = data.get("model_id") or MODEL
    Database.save_model(user, model_id)
    return {"ok": True}


@app.post("/api/language")
async def api_set_language(request: Request, session_user: str | None = Cookie(default=None)):
    user = get_current_user(session_user)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in."}, status_code=401)
    data = await request.json()
    lang = data.get("lang") or "en"
    Database.save_language(user, lang)
    resp = JSONResponse({"ok": True})
    # Keep the pre-login screen in sync with this browser's last-known
    # preference (best-effort only — the real source of truth is the
    # per-user entry in language_pref.json).
    resp.set_cookie("ui_lang", lang, max_age=60 * 60 * 24 * 365, samesite="lax")
    return resp


@app.post("/api/chats/{chat_id}/clear")
def api_clear_chat(chat_id: str, session_user: str | None = Cookie(default=None)):
    """Resets a conversation back to empty, mirroring the desktop app's
    'Clear current conversation' settings-menu action. The chat entry
    itself (id, sidebar slot) is kept - only its messages are wiped."""
    user = get_current_user(session_user)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in."}, status_code=401)
    messages = [dict(SYSTEM_PROMPT)]
    Database.save_chat(user, chat_id, None, messages)
    return {"ok": True}


# ============================================================
#                    STREAMING CHAT (SSE)
# ============================================================
@app.post("/api/chats/{chat_id}/send")
async def api_send_message(chat_id: str, request: Request, session_user: str | None = Cookie(default=None)):
    user = get_current_user(session_user)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in."}, status_code=401)

    data = await request.json()
    text = (data.get("text") or "").strip()
    if not text:
        return JSONResponse({"ok": False, "error": "Empty message."}, status_code=400)

    model_id = Database.load_model(user)

    if Database.chat_exists(user, chat_id):
        messages = Database.load_chat(user, chat_id)
    else:
        messages = [dict(SYSTEM_PROMPT)]

    is_first_message = not any(m.get("role") == "user" for m in messages)
    messages.append({"role": "user", "content": text})

    def event_stream():
        full_reply = ""
        # Let the client know if this is the first message (for title update)
        title_payload = json.dumps({"type": "meta", "is_first": is_first_message})
        yield f"data: {title_payload}\n\n"

        for chunk in stream_chat(messages, model_id):
            full_reply += chunk
            payload = json.dumps({"type": "chunk", "text": chunk})
            yield f"data: {payload}\n\n"

        messages.append({"role": "assistant", "content": full_reply})

        title = None
        for m in messages:
            if m.get("role") == "user":
                title = m.get("content", "")[:60]
                break

        Database.save_chat(user, chat_id, title, messages)

        done_payload = json.dumps({"type": "done", "title": title})
        yield f"data: {done_payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)