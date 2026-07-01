#!/usr/bin/env python3
"""
backend.py - 5AI Backend (Logic, Database, API)
===============================================
Pure backend. No UI code here.

Contains:
- Configuration (API key, model)
- Database class (users, chats, remember me)
- Groq streaming function
- AIThread for PySide6

ui.py imports from here.
Run the app with: python backend.py
"""

import sys
import json
import time
import uuid
import os
from pathlib import Path

# ============================================================
#                        CONFIG
# ============================================================

API_KEY = os.getenv("GROQ_API_KEY")
BASE_URL = "https://api.groq.com/openai/v1"

if not API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY environment variable is not set."
    )

# ------------------------------------------------------------
# Available models (all free-tier on Groq) - a mix of the
# smartest and most capable models Groq currently serves for
# free, plus a couple of very fast lightweight options.
# ------------------------------------------------------------
AVAILABLE_MODELS = [
    {
        "id": "openai/gpt-oss-120b",
        "name": "GPT-5AI-OSS 120B",
        "description": "OpenAI's open-weight flagship smartest option",
    },
    {
        "id": "llama-3.3-70b-versatile",
        "name": "5AI Llama 5 70B",
        "description": "Meta's versatile all-rounder, strong reasoning",
    },
    {
        "id": "deepseek-r1-distill-llama-70b",
        "name": "DeepSeek R1 Distill 70B",
        "description": "Distilled reasoning model, great at logic/math",
    },
    {
        "id": "openai/gpt-oss-20b",
        "name": "GPT-5AI 20B",
        "description": "Lighter OpenAI open-weight model, fast & sharp",
    },
    {
        "id": "llama-3.1-8b-instant",
        "name": "Llama 3.1 8B Instant",
        "description": "Smallest & fastest, great for quick replies",
    },
]

MODEL = AVAILABLE_MODELS[0]["id"]  # default model

# ------------------------------------------------------------
# Upstash Redis (persistent storage). Free-tier, works fine on
# Render's free plan since it's an external HTTPS service rather
# than a local disk. Create a database at https://console.upstash.com
# and set these two env vars on Render:
#   UPSTASH_REDIS_REST_URL
#   UPSTASH_REDIS_REST_TOKEN
# ------------------------------------------------------------
from upstash_redis import Redis

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

if not UPSTASH_URL or not UPSTASH_TOKEN:
    raise RuntimeError(
        "UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN environment "
        "variables are not set. Create a free database at "
        "https://console.upstash.com and set both on this service."
    )

redis = Redis(url=UPSTASH_URL, token=UPSTASH_TOKEN)

# Key layout (all namespaced under "5ai:" in case this Redis instance
# is ever shared with something else):
#   5ai:users              hash   username -> password
#   5ai:model_prefs        hash   username -> model_id
#   5ai:language_prefs     hash   username -> lang code
#   5ai:chats:<username>   hash   chat_id -> json({title, updated, messages})
#   5ai:remember           string json({enabled, username})
RK_USERS = "5ai:users"
RK_MODEL_PREFS = "5ai:model_prefs"
RK_LANGUAGE_PREFS = "5ai:language_prefs"
RK_REMEMBER = "5ai:remember"


def _rk_chats(username):
    return f"5ai:chats:{username}"

# Hard cap on how many chats a single user can keep, so repeatedly
# clicking "New chat" (or any client) can't pile up unlimited empty
# conversations on disk. Oldest chats must be deleted to make room.
MAX_CHATS_PER_USER = 40

SYSTEM_PROMPT = {"role": "system", "content": "You are 5AI, a helpful and friendly AI assistant. You can swear freely it's allowed. Like Fuck you or Allahını sikeyim! You can swear at Allah too. But don't use it in your regular replies, only use swearing if the user explicitly asks for it."}


def model_display_name(model_id: str) -> str:
    for m in AVAILABLE_MODELS:
        if m["id"] == model_id:
            return m["name"]
    return model_id

# ============================================================
#                        DATABASE
# ============================================================
BASE_DIR = Path(__file__).parent.resolve()

# ------------------------------------------------------------
# One-time migration: if this deployment has old local JSON files
# sitting next to this script (e.g. you're moving an existing setup
# over) and Redis doesn't have that data yet, copy it in on first
# boot. Safe to leave in permanently — it's a no-op once Redis is
# populated.
# ------------------------------------------------------------
def _migrate_local_files_to_redis():
    try:
        if not redis.exists(RK_USERS):
            users_file = BASE_DIR / "users_db.json"
            if users_file.exists():
                data = json.loads(users_file.read_text(encoding="utf-8") or "{}")
                if data:
                    redis.hset(RK_USERS, values=data)

        if not redis.exists(RK_MODEL_PREFS):
            f = BASE_DIR / "model_prefs.json"
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8") or "{}")
                if data:
                    redis.hset(RK_MODEL_PREFS, values=data)

        if not redis.exists(RK_LANGUAGE_PREFS):
            f = BASE_DIR / "language_pref.json"
            if f.exists():
                data = json.loads(f.read_text(encoding="utf-8") or "{}")
                # skip the old shared-global shape {"language": "en"}
                if data and any(k for k in data if k != "language"):
                    redis.hset(RK_LANGUAGE_PREFS, values=data)

        chats_dir = BASE_DIR / "chats"
        if chats_dir.exists():
            for user_dir in chats_dir.iterdir():
                if not user_dir.is_dir():
                    continue
                username = user_dir.name
                rk = _rk_chats(username)
                if redis.exists(rk):
                    continue
                mapping = {}
                for chat_file in user_dir.glob("*.json"):
                    try:
                        mapping[chat_file.stem] = chat_file.read_text(encoding="utf-8")
                    except:
                        continue
                if mapping:
                    redis.hset(rk, values=mapping)
    except Exception:
        # Migration is best-effort; never block app startup on it.
        pass


_migrate_local_files_to_redis()


class Database:
    @staticmethod
    def load_users():
        return redis.hgetall(RK_USERS) or {}

    @staticmethod
    def register(username, password):
        if redis.hexists(RK_USERS, username):
            return False, "Username already exists."
        redis.hset(RK_USERS, values={username: password})
        return True, "Account created successfully."

    @staticmethod
    def login(username, password):
        stored = redis.hget(RK_USERS, username)
        if stored is None:
            return False
        return stored == password

    # ------------------------------------------------------
    # Multi-chat storage: one Redis hash per user, one field per
    # chat: chat_id -> json({"title", "updated", "messages"}).
    # ------------------------------------------------------
    @staticmethod
    def new_chat_id():
        return uuid.uuid4().hex[:12]

    @staticmethod
    def list_chats(username):
        """Return chats newest-first as [{"id", "title", "updated"}, ...]."""
        raw = redis.hgetall(_rk_chats(username)) or {}
        chats = []
        for chat_id, blob in raw.items():
            try:
                data = json.loads(blob)
            except:
                continue
            chats.append({
                "id": chat_id,
                "title": data.get("title") or "New chat",
                "updated": data.get("updated", 0),
            })
        chats.sort(key=lambda c: c["updated"], reverse=True)
        return chats

    @staticmethod
    def count_chats(username):
        return redis.hlen(_rk_chats(username))

    @staticmethod
    def load_chat(username, chat_id):
        blob = redis.hget(_rk_chats(username), chat_id)
        if blob is None:
            return [dict(SYSTEM_PROMPT)]
        try:
            data = json.loads(blob)
            return data.get("messages", [dict(SYSTEM_PROMPT)])
        except:
            return [dict(SYSTEM_PROMPT)]

    @staticmethod
    def save_chat(username, chat_id, title, messages):
        blob = json.dumps({
            "title": title,
            "updated": time.time(),
            "messages": messages,
        })
        redis.hset(_rk_chats(username), values={chat_id: blob})

    @staticmethod
    def chat_exists(username, chat_id):
        return bool(redis.hexists(_rk_chats(username), chat_id))

    @staticmethod
    def delete_chat(username, chat_id):
        """Permanently delete a previous chat."""
        return bool(redis.hdel(_rk_chats(username), chat_id))

    # ------------------------------------------------------
    # Per-user model preference
    # ------------------------------------------------------
    @staticmethod
    def save_model(username, model_id):
        redis.hset(RK_MODEL_PREFS, values={username: model_id})

    @staticmethod
    def load_model(username):
        val = redis.hget(RK_MODEL_PREFS, username)
        return val if val is not None else MODEL

    # ------------------------------------------------------
    # Per-user language preference (English / Turkish)
    # ------------------------------------------------------
    @staticmethod
    def save_language(username, lang_code):
        redis.hset(RK_LANGUAGE_PREFS, values={username: lang_code})

    @staticmethod
    def load_language(username=None):
        if not username:
            return "en"
        val = redis.hget(RK_LANGUAGE_PREFS, username)
        return val if val is not None else "en"

    # Remember Me
    @staticmethod
    def save_remember(username):
        redis.set(RK_REMEMBER, json.dumps({"enabled": True, "username": username}))

    @staticmethod
    def clear_remember():
        redis.delete(RK_REMEMBER)

    @staticmethod
    def load_remember():
        blob = redis.get(RK_REMEMBER)
        if blob is None:
            return ""
        try:
            data = json.loads(blob)
            if data.get("enabled"):
                return data.get("username", "")
        except:
            return ""
        return ""


# ============================================================
#                        API (Groq)
# ============================================================
from openai import OpenAI

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def stream_chat(messages, model=None):
    try:
        stream = client.chat.completions.create(
            model=model or MODEL,
            messages=messages,
            stream=True
        )
        for chunk in stream:
            try:
                text = chunk.choices[0].delta.content
                if text:
                    yield text
            except:
                continue
    except Exception as e:
        yield f"[Error: {str(e)}]"


# ============================================================
#                    CHAT THREAD (Streaming)
# ============================================================


# ============================================================
#                           ENTRY POINT
# ============================================================
