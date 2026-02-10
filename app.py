import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import shutil
import uuid
from datetime import datetime

app = FastAPI(title="نظام الرد على الاستفسارات")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
files_db = []

class ChatRequest(BaseModel):
    message: str

@app.get("/")
async def root():
    return {"message": "النظام يعمل!", "chat": "/chat", "admin": "/admin"}

@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    with open("chat.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    with open("admin.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/chat")
async def chat(request: ChatRequest):
    return {"response": f"تم استلام رسالتك: {request.message} (النظام في وضع الاختبار)"}

@app.post("/admin/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "PDF فقط")
    fid = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, f"{fid}_{file.filename}")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    files_db.append({"id": fid, "filename": file.filename, "path": path})
    return {"message": "تم الرفع"}

@app.get("/admin/files")
async def list_files():
    return files_db

@app.delete("/admin/files/{fid}")
async def delete(fid: str):
    global files_db
    files_db = [x for x in files_db if x["id"] != fid]
    return {"message": "تم الحذف"}

