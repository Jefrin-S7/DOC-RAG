import os
import warnings
import threading
import time
warnings.filterwarnings("ignore", category=FutureWarning)

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from drive import get_all_pdfs
from embeddings import build_index, search, index_exists
from nvidia_llm import ask

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "../.env.local"))

FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
TOP_K = int(os.getenv("TOP_K", 5))

app = FastAPI(title="DOC ASSISTANT CHATBOT", version="1.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#memory status

indexing_status = {
    "status": "idle",
    "message": "No documents loaded yet.",
    "file_count": 0,
}

#verion 2 - conversation history

class Message(BaseModel):
    role: str
    content: str

#pydantic models

class QuestionRequest(BaseModel):
    question: str
    top_k: int = TOP_K
    history: list[Message]= []

class QuestionResponse(BaseModel):
    answer: str
    sources: list
    model: str
    tokens_used: int
    chunks_used: list[dict]

#Background indexing

def run_indexing():
    global indexing_status
    try:
        indexing_status = {
            "status": "loading",
            "message": "Connecting to Google Drive ....",
            "file_count": 0,
        }

        pdf_files = get_all_pdfs(FOLDER_ID)

        if not pdf_files:
            indexing_status = {
                "status": "error",
                "message": "No PDF files found in the Folder.",
                "file_count": 0,
            }
            return
        
        indexing_status = {
            "status": "indexing",
            "message": f"Indexing {len(pdf_files)} file(s)...",
            "file_count": len(pdf_files),
        }

        build_index(pdf_files)

        indexing_status = {
            "status": "ready",
            "message": f"Successfully indexed {len(pdf_files)} file(s).",
            "file_count": len(pdf_files),
        }

    except Exception as e:
        indexing_status = {
            "status": "error",
            "message": str(e),
            "file_count": 0,
        }

# v2 - reload task
def run_reload():
    global indexing_status
    try:
        indexing_status = {
            "status": "loading",
            "message": "Clearing old pinecone index...",
            "file_count": 0,

        }

        from pinecone import Pinecone
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index(os.getenv("PINECONE_INDEX", "doc-rag-index"))
        index.delete(delete_all=True)
        print("[Reload] Old index cleared.", flush=True)

        run_indexing()   
    except Exception as e:
        indexing_status = {
            "status": "error",
            "message": str(e),
            "file_count": 0,
        }

# Kepp alive ping for render

#startup
# @app.on_event("startup")
# async def startup_event():
#     global indexing_status
#     try:
#         if index_exists():
#             indexing_status = {
#                 "status": "ready",
#                 "message": "Index loaded from the pinecone.",
#                 "file_count": 0,
#             }

#             print("[Startup] Pinecone index found")
#         else:
#             print("[startp] No index - call/load to build one")
#     except Exception as e:
#         print(f"[Startup] Warning: {e}")
        
  



#Routes

@app.get("/")
def root():
    return {"message": "DOC-RAG API is running. Visit /docs"}


@app.post("/load")
def load_documents(background_tasks: BackgroundTasks):
    if indexing_status["status"] in ("loading", "indexing"):
        return {"message": "Indexing in progress.", "status": indexing_status}
    background_tasks.add_task(run_indexing)
    return {"message": "Started loading documents from Google Drive."}

@app.get("/status")
def get_status():
    return {**indexing_status, "index_exists": index_exists()}

@app.post("/ask", response_model=QuestionResponse)
def ask_question(req: QuestionRequest):
    if not index_exists():
        raise HTTPException(
            status_code=400,
            detail="No documents indexed yet. Call POST /load first."
        )
    
    if not req.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )
    
    chunks = search(req.question, top_k=req.top_k)
    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No relevant chunks found."
        )
    
    result = ask(req.question, chunks)

    return QuestionResponse(
        answer = result["answer"],
        sources = result["sources"],
        model = result["model"],
        tokens_used = result["tokens_used"],
        chunks_used = chunks,
    )

@app.get("/health")
def health():
    return {"status": "ok", "index_ready": index_exists()}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("BACKEND_PORT", 8000)))
    uvicorn.run("main:app", host=host, port=port, reload=False)
