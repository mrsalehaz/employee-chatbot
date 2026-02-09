import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import shutil
import uuid
from datetime import datetime
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
import PyPDF2

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

CUSTOM_PROMPT = """
أنت مساعد ذكي لشركة حكومية سعودية. عليك الرد على استفسارات الموظفين بناءً على الأنظمة واللوائح المرفقة فقط.

قواعد صارمة:
1. كن مهذبًا (استخدم "حياك الله"، "تفضل")
2. لا ترد على الاستفزازات
3. إذا لم يكن الجواب في المستندات، اعتذر بأدب
4. ختم الرد بـ "هل لديك استفسار آخر؟"

السياق: {context}
السؤال: {question}
الرد:
"""

prompt = PromptTemplate(template=CUSTOM_PROMPT, input_variables=["context", "question"])

def is_offensive(text):
    words = ["غبي", "احمق", "stupid", "حرامي", "كلب"]
    return any(w in text.lower() for w in words)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
async def root():
    return {"status": "online", "chat": "/chat", "admin": "/admin"}

@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    with open("frontend/chat.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    with open("frontend/admin.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/chat")
async def chat(request: ChatRequest):
    if is_offensive(request.message):
        return {"response": "أعتذر، أنا هنا لمساعدتك فقط. كيف يمكنني خدمتك؟"}
    
    if not files_db:
        return {"response": "لم يتم رفع الأنظمة بعد. راجع المسؤول."}
    
    try:
        embeddings = OpenAIEmbeddings()
        db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
        retriever = db.as_retriever(search_kwargs={"k": 3})
        
        qa = RetrievalQA.from_chain_type(
            llm=ChatOpenAI(temperature=0, model="gpt-3.5-turbo"),
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt}
        )
        result = qa({"query": request.message})
        return {"response": result["result"]}
    except Exception as e:
        return {"response": "عذراً، حدث خطأ. تأكد من إعداد OpenAI API Key."}

@app.post("/admin/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "PDF فقط")
    
    fid = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, f"{fid}_{file.filename}")
    
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        text = extract_text(path)
        chunks = split_text(text)
        
        emb = OpenAIEmbeddings()
        db = Chroma.from_texts(chunks, emb, persist_directory="./chroma_db")
        db.persist()
        
        files_db.append({"id": fid, "filename": file.filename, "date": datetime.now().isoformat(), "path": path})
        return {"message": "تم الرفع بنجاح"}
    except Exception as e:
        if os.path.exists(path):
            os.remove(path)
        raise HTTPException(500, str(e))

@app.get("/admin/files")
async def list_files():
    return files_db

@app.delete("/admin/files/{fid}")
async def delete(fid: str):
    global files_db
    f = next((x for x in files_db if x["id"] == fid), None)
    if f and os.path.exists(f["path"]):
        os.remove(f["path"])
    files_db = [x for x in files_db if x["id"] != fid]
    return {"message": "تم الحذف"}

def extract_text(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as f:
        r = PyPDF2.PdfReader(f)
        for p in r.pages:
            t = p.extract_text()
            if t: 
                text += t + "\n"
    return text

def split_text(text):
    s = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return s.split_text(text)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
