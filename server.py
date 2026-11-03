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

class RegisterIn(LoginIn):
    email: str

class ChatIn(BaseModel):
    question: str
    conversation_id: int | None = None
    save_user: bool = True

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "edgesight.html")

@app.post("/api/login")
def login(data: LoginIn, request: Request):
    user = login_user(data.username.strip(), data.password)
    if not user:
        return {"error": "Invalid username or password."}
    request.session["user"] = user
    return user

@app.post("/api/register")
def register(data: RegisterIn):
    ok, msg = validate_account(data.username, data.email, data.password)
    if not ok:
        return {"error": msg}
    ok, msg = register_user(data.username.strip(), data.email.strip().lower(), data.password)
    return {"ok": ok, "message": msg}

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