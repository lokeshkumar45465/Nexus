import ollama
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from auth import login_user, register_user, validate_account
from chat_history import (
    create_conversation, get_user_conversations,
    get_conversation_messages, save_message, delete_conversation,
)
from data_loader import get_dataset_from_database, refresh_database
from rag_engine import generate_rag_answer, index_documents

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("EDGESIGHT_SECRET", "change-this-secret"),
    same_site="lax",
)

_df = None
def get_df():
    global _df
    if _df is None:
        _df = get_dataset_from_database()
    return _df

def current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(401, "Not logged in")
    return user

def admin_user(request: Request):
    user = current_user(request)
    if user["role"] != "admin":
        raise HTTPException(403, "Admins only")
    return user

class LoginIn(BaseModel):
    username: str
    password: str



class ChatIn(BaseModel):
    question: str
    conversation_id: int | None = None
    save_user: bool = True

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "edgesight.html")

@app.get("/api/models")
def get_models(request: Request):
    current_user(request)

    try:
        response = ollama.list()
        return [model.model for model in response.models]

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to Ollama: {error}"
        )
        
@app.post("/api/login")
def login(data: LoginIn, request: Request):
    user = login_user(data.username.strip(), data.password)
    if not user:
        return {"error": "Invalid username or password."}
    request.session["user"] = user
    return user


@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}

@app.get("/api/me")
def me(request: Request):
    return request.session.get("user") or {}

@app.get("/api/conversations")
def conversations(request: Request):
    return get_user_conversations(current_user(request)["user_id"])

@app.get("/api/conversations/{cid}")
def messages(cid: int, request: Request):
    return get_conversation_messages(current_user(request)["user_id"], cid)

@app.delete("/api/conversations/{cid}")
def remove(cid: int, request: Request):
    return {"ok": delete_conversation(current_user(request)["user_id"], cid)}

@app.post("/api/chat")
async def chat(data: ChatIn, request: Request):
    uid = current_user(request)["user_id"]
    cid = data.conversation_id
    if cid is None:
        cid = create_conversation(uid, data.question.strip()[:40] or "New Chat")
    history = get_conversation_messages(uid, cid)
    if data.save_user:
        save_message(uid, cid, "user", data.question)
    answer = generate_rag_answer(data.question, get_df(), history)
    save_message(uid, cid, "assistant", answer)
    return {"answer": answer, "conversation_id": cid}

@app.post("/api/admin/reindex")
def reindex(request: Request):
    admin_user(request)
    return index_documents()

@app.post("/api/admin/refresh")
def refresh(request: Request):
    global _df
    admin_user(request)
    refresh_database()
    _df = None
    return {"ok": True}


import secrets
import sqlite3
from auth import hash_password
from database import get_connection, initialize_database

def migrate():
    initialize_database()
    conn = get_connection()
    for col in ("position TEXT DEFAULT 'Operations Engineer'", "company TEXT"):
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col}")
        except Exception:
            pass
    conn.commit()
    conn.close()
migrate()

class RegisterIn(LoginIn):
    email: str
    company: str = ""
    position: str = "Operations Engineer"

@app.post("/api/register")
def register(data: RegisterIn):
    ok, msg = validate_account(data.username, data.email, data.password)
    if not ok:
        return {"error": msg}
    email = data.email.strip().lower()
    ok, msg = register_user(data.username.strip(), email, data.password)
    if ok:
        conn = get_connection()
        conn.execute("UPDATE users SET position=?, company=? WHERE email=?",
                     (data.position, data.company, email))
        conn.commit()
        conn.close()
    return {"ok": ok, "message": msg}

@app.get("/api/admin/users")
def admin_list(request: Request):
    admin_user(request)
    conn = get_connection()
    rows = conn.execute("SELECT user_id, username, email, role, position, is_active, created_at FROM users ORDER BY user_id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

class UserPatch(BaseModel):
    role: str | None = None
    active: bool | None = None

@app.patch("/api/admin/users/{uid}")
def admin_patch(uid: int, data: UserPatch, request: Request):
    me = admin_user(request)
    if uid == me["user_id"]:
        raise HTTPException(400, "You can't change your own account.")
    conn = get_connection()
    try:
        if data.role in ("user", "admin"):
            target = conn.execute("SELECT role FROM users WHERE user_id=?", (uid,)).fetchone()
            admins = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
            if data.role == "user" and target and target["role"] == "admin" and admins < 2:
                raise HTTPException(400, "At least one admin is required.")
            conn.execute("UPDATE users SET role=? WHERE user_id=?", (data.role, uid))
        if data.active is not None:
            conn.execute("UPDATE users SET is_active=? WHERE user_id=?", (int(data.active), uid))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}

@app.delete("/api/admin/users/{uid}")
def admin_delete(uid: int, request: Request):
    me = admin_user(request)
    if uid == me["user_id"]:
        raise HTTPException(400, "You can't delete your own account.")
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    return {"ok": True}

class NewUser(BaseModel):
    name: str
    email: str
    role: str = "user"
    position: str = "Operations Engineer"

@app.post("/api/admin/users")
def admin_create(data: NewUser, request: Request):
    admin_user(request)
    temp = secrets.token_urlsafe(8)
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, email, password_hash, role, position) VALUES (?,?,?,?,?)",
            (data.name.strip(), data.email.strip().lower(), hash_password(temp),
             data.role if data.role in ("user", "admin") else "user", data.position))
        conn.commit()
    except sqlite3.IntegrityError:
        return {"error": "Username or email already exists."}
    finally:
        conn.close()
    return {"ok": True, "temp_password": temp}