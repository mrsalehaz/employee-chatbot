import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
files_db = []

class ChatRequest(BaseModel):
    message: str

@app.get("/")
async def root():
    # قائمة الملفات للتشخيص
    try:
        files_in_dir = os.listdir(BASE_DIR)
        frontend_exists = os.path.exists(os.path.join(BASE_DIR, "frontend"))
        if frontend_exists:
            frontend_files = os.listdir(os.path.join(BASE_DIR, "frontend"))
        else:
            frontend_files = "مجلد frontend غير موجود!"
    except Exception as e:
        files_in_dir = str(e)
        frontend_files = "خطأ في القراءة"
    
    return {
        "message": "النظام يعمل!",
        "base_dir": BASE_DIR,
        "files_in_root": files_in_dir,
        "frontend_exists": frontend_exists,
        "frontend_files": frontend_files
    }

@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    try:
        filepath = os.path.join(BASE_DIR, "frontend", "chat.html")
        if not os.path.exists(filepath):
            return f"""
            <h1>خطأ: الملف غير موجود</h1>
            <p>المسار: {filepath}</p>
            <p>المجلدات في BASE_DIR: {os.listdir(BASE_DIR)}</p>
            """
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"<h1>خطأ داخلي</h1><p>{str(e)}</p>"

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    try:
        filepath = os.path.join(BASE_DIR, "frontend", "admin.html")
        if not os.path.exists(filepath):
            return f"""
            <h1>خطأ: الملف غير موجود</h1>
            <p>المسار: {filepath}</p>
            <p>المجلدات في BASE_DIR: {os.listdir(BASE_DIR)}</p>
            """
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"<h1>خطأ داخلي</h1><p>{str(e)}</p>"

@app.post("/chat")
async def chat(request: ChatRequest):
    return {"response": f"تم استلام رسالتك: {request.message}"}

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
