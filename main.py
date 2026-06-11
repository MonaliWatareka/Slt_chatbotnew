"""
backend/main.py — FastAPI backend for SLT Insight chatbot
Updated: Added /logo2 endpoint for new SLT logo
Run with: uvicorn main:app --reload --port 8000
"""

import os
import io
import json
import tempfile
import base64
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from graph.slt_graph       import run_graph
from rag.pdf_loader        import load_and_split_pdf
from rag.embedder          import create_vectorstore
from rag.knowledge_base    import load_knowledge_base, build_knowledge_base
from analysis.excel_reader import load_excel

app = FastAPI(title="SLT Insight API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict = {}

LOGO_PATH     = "F:/Slt_chatbotnew/sltlogo.png"
LOGO_NEW_PATH = "F:/Slt_chatbotnew/slt_logo_new.be681e06.png"

def get_session(session_id: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = {
            "messages":       [],
            "vectorstore":    None,
            "df":             None,
            "pdf_names":      [],
            "excel_name":     None,
            "model":          "llama3.2",
            "vision_model":   "llava",
            "kb_vectorstore": None,
            "image_file":     None,
            "image_name":     None,
            "active_flow":    None,
            "flow_answers":   {},
        }
    return sessions[session_id]


@app.on_event("startup")
async def startup_event():
    try:
        kb = load_knowledge_base()
        app.state.kb_vectorstore = kb
        print("[API] Knowledge base loaded." if kb else "[API] No KB found.")
    except Exception as e:
        app.state.kb_vectorstore = None
        print(f"[API] KB load error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id:   str
    message:      str
    model:        Optional[str] = "llama3.2"
    vision_model: Optional[str] = "llava"

class FeedbackRequest(BaseModel):
    session_id: str
    msg_id:     str
    rating:     str
    content:    str


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "SLT Insight API running", "version": "2.0.0"}


@app.get("/health")
def health():
    kb_loaded = getattr(app.state, "kb_vectorstore", None) is not None
    return {"status": "ok", "kb_loaded": kb_loaded}


# ── Original logo ──────────────────────────────────────────────
@app.get("/logo")
def get_logo():
    if os.path.exists(LOGO_PATH):
        return FileResponse(LOGO_PATH, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo not found")


# ── New logo ───────────────────────────────────────────────────
@app.get("/logo2")
def get_logo2():
    # Try new logo first, fall back to original if not found
    if os.path.exists(LOGO_NEW_PATH):
        return FileResponse(LOGO_NEW_PATH, media_type="image/png")
    if os.path.exists(LOGO_PATH):
        return FileResponse(LOGO_PATH, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo not found")


# ── Chat ───────────────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    session = get_session(req.session_id)
    session["model"]          = req.model
    session["vision_model"]   = req.vision_model
    session["kb_vectorstore"] = getattr(app.state, "kb_vectorstore", None)

    try:
        result = run_graph(req.message, session)

        session["active_flow"]  = result.get("active_flow")
        session["flow_answers"] = result.get("flow_answers") or {}
        session["messages"].append({"role": "user",      "content": req.message})
        session["messages"].append({"role": "assistant", "content": result.get("response", "")})

        fig_json = None
        fig = result.get("figure")
        if fig:
            fig_json = fig.to_json()

        return {
            "response":     result.get("response", ""),
            "intent":       result.get("intent", "chat"),
            "active_flow":  result.get("active_flow"),
            "flow_answers": result.get("flow_answers", {}),
            "sources":      result.get("sources", []),
            "figure":       fig_json,
            "error":        result.get("error"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Upload PDF ─────────────────────────────────────────────────
@app.post("/upload/pdf")
async def upload_pdf(
    session_id: str = Form(...),
    files: list[UploadFile] = File(...),
):
    session    = get_session(session_id)
    all_chunks = []
    names      = []

    for file in files:
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            chunks = load_and_split_pdf(tmp_path)
            all_chunks.extend(chunks)
            names.append(file.filename)
        finally:
            os.unlink(tmp_path)

    if all_chunks:
        session["vectorstore"] = create_vectorstore(all_chunks, model=session["model"])
        session["pdf_names"]   = names

    return {"success": True, "files": names, "chunks": len(all_chunks)}


# ── Upload Excel ───────────────────────────────────────────────
@app.post("/upload/excel")
async def upload_excel(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    session        = get_session(session_id)
    content        = await file.read()
    file_like      = io.BytesIO(content)
    file_like.name = file.filename

    df, _ = load_excel(file_like)
    session["df"]         = df
    session["excel_name"] = file.filename

    stats = {
        "rows":         len(df),
        "columns":      len(df.columns),
        "preview":      df.head(5).to_dict(orient="records"),
        "column_names": list(df.columns),
    }
    return {"success": True, "filename": file.filename, "stats": stats}


# ── Upload Image ───────────────────────────────────────────────
@app.post("/upload/image")
async def upload_image(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    session        = get_session(session_id)
    content        = await file.read()
    file_like      = io.BytesIO(content)
    file_like.name = file.filename
    file_like.seek(0)

    session["image_file"] = file_like
    session["image_name"] = file.filename

    img_b64 = base64.b64encode(content).decode()
    return {
        "success":  True,
        "filename": file.filename,
        "preview":  f"data:image/jpeg;base64,{img_b64}",
    }


# ── Session status ─────────────────────────────────────────────
@app.get("/session/{session_id}")
def session_status(session_id: str):
    session = get_session(session_id)
    return {
        "has_pdf":       session.get("vectorstore") is not None,
        "has_excel":     session.get("df") is not None,
        "has_image":     session.get("image_file") is not None,
        "has_kb":        session.get("kb_vectorstore") is not None,
        "pdf_names":     session.get("pdf_names", []),
        "excel_name":    session.get("excel_name"),
        "image_name":    session.get("image_name"),
        "active_flow":   session.get("active_flow"),
        "model":         session.get("model", "llama3.2"),
        "vision_model":  session.get("vision_model", "llava"),
        "message_count": len(session.get("messages", [])),
    }


# ── Clear session ──────────────────────────────────────────────
@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    if session_id in sessions:
        sessions[session_id] = {
            "messages":       [],
            "vectorstore":    None,
            "df":             None,
            "pdf_names":      [],
            "excel_name":     None,
            "model":          "llama3.2",
            "vision_model":   "llava",
            "image_file":     None,
            "image_name":     None,
            "active_flow":    None,
            "flow_answers":   {},
            "kb_vectorstore": getattr(app.state, "kb_vectorstore", None),
        }
    return {"success": True}


# ── Feedback ───────────────────────────────────────────────────
@app.post("/feedback")
async def feedback(req: FeedbackRequest):
    import csv, datetime
    path        = "F:/Slt_chatbotnew/feedback_log.csv"
    row         = [
        datetime.datetime.now().isoformat(),
        req.session_id,
        str(req.msg_id),
        req.rating,
        req.content[:100].replace("\n", " "),
    ]
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["timestamp", "session_id", "msg_id", "rating", "content"])
        w.writerow(row)
    return {"success": True}


# ── Build KB ───────────────────────────────────────────────────
@app.post("/kb/build")
async def build_kb():
    try:
        kb = build_knowledge_base()
        app.state.kb_vectorstore = kb
        return {"success": True, "message": "Knowledge base built successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Export chat ────────────────────────────────────────────────
@app.get("/export/{session_id}")
def export_chat(session_id: str):
    session  = get_session(session_id)
    messages = session.get("messages", [])
    text     = "\n\n".join(
        f"[{m['role'].upper()}]\n{m['content']}"
        for m in messages
    )
    return StreamingResponse(
        io.StringIO(text),
        media_type = "text/plain",
        headers    = {"Content-Disposition": f"attachment; filename=slt_chat_{session_id}.txt"},
    )