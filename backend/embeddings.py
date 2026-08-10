# import os
# import fitz
# import numpy as np
# from pinecone import Pinecone, ServerlessSpec
# import requests
# from sentence_transformers import SentenceTransformer
# from dotenv import load_dotenv

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# load_dotenv(os.path.join(BASE_DIR, "../.env.local"))

# PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
# INDEX_NAME= os.getenv("PINECONE_INDEX", "doc-rag-index")
# EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
# CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1200))
# CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 150))
# TOP_K = int(os.getenv("TOP_K", 5))


# _model = None

# #Embedding model

# def get_model() -> SentenceTransformer:
#     global _model
#     if _model is None:
#         print(f"[Embeddings] Loading model: {EMBEDDING_MODEL}", flush=True)
#         _model = SentenceTransformer(EMBEDDING_MODEL)
#     return _model

# #Pinecone 

# def get_pinecone_index():
#     PC = Pinecone(api_key=PINECONE_API_KEY)
#     existing = [i.name for i in PC.list_indexes()]

#     if INDEX_NAME not in existing:
#         print(f"[Pinecone] Creating index: {INDEX_NAME}", flush=True)
#         PC.create_index(
#             name=INDEX_NAME,
#             dimension=384,
#             metric="cosine",
#             spec=ServerlessSpec(cloud="aws", region="us-east-1")
#         )
#         print("[Pinecone] Index created", flush=True)

#     return PC.Index(INDEX_NAME)

# #Extract text

# def extract_text(pdf_bytes: bytes) -> str:
#     doc = fitz.open(stream=pdf_bytes, filetype="pdf")
#     full_text = ""
#     for page_num, page in enumerate(doc):
#         full_text += f"\n--- Page {page_num + 1} ---\n"
#         full_text += page.get_text()
#     doc.close()
#     return full_text

# # Chunk text

# def chunk_text(text: str) -> list:
#     chunks = []
#     start = 0
#     while start < len(text):
#         chunks.append(text[start:start + CHUNK_SIZE])
#         start += CHUNK_SIZE - CHUNK_OVERLAP
#     return chunks

# #Build Index

# def build_index(pdf_files: list) -> tuple:
#     model = get_model()
#     all_chunks = []

#     for pdf in pdf_files:
#         print(f"[Chunking] {pdf['name']}", flush=True)
#         text = extract_text(pdf["bytes"])
#         chunks = chunk_text(text)
#         print(f" -> {len(chunks)} chunks", flush=True)
#         for chunk in chunks:
#             all_chunks.append({
#                 "text": chunk,
#                 "source": pdf["name"],
#             })


#     print(f"\n[Embeddings] Total chunks: {len(all_chunks)}", flush=True)
#     print("[Embeddings] Creating embeddings...", flush=True)

#     texts = [c["text"] for c in all_chunks]
#     embeddings = model.encode(
#         texts,
#         show_progress_bar=True,
#         batch_size=64
#     )

#     print("[Pinecone] Uploading vectors...", flush=True)
#     index = get_pinecone_index()
#     batch_size = 200

#     # for attempt in range(3):
#     # try:
#     #     index.upsert(vectors=vectors)
#     #     break
#     # except Exception as e:
#     #     print(f"Retry {attempt + 1}: {e}", flush=True)
#     #     time.sleep(2)

#     for i in range(0, len(all_chunks), batch_size):
#         batch_chunks = all_chunks[i:i + batch_size]
#         batch_embeds = embeddings[i:i + batch_size]
#         vectors = [
#             {
#                 "id": str(i + j),
#                 "values": emb.tolist(),
#                 "metadata": {
#                     "text": chunk["text"],
#                     "source": chunk["source"],
#                 }
#             }
#             for j, (chunk, emb) in enumerate(zip(batch_chunks, batch_embeds))
#         ]
#         index.upsert(vectors=vectors)
#         print(f"[Pinecone] Batch {i // batch_size +1}", flush=True)

#     print(f"[Pinecone] Done - {len(all_chunks)} vectors stored", flush=True)

#     return index, all_chunks
    

# # Search similar chunks

# def search(query: str, top_k: int = TOP_K) -> list:
#     model = get_model()
#     index = get_pinecone_index()
#     query_vec = model.encode([query])[0].tolist()

#     results = index.query(vector=query_vec, top_k=top_k, include_metadata=True)

#     return [
#         {
#             "text": match["metadata"]["text"],
#             "source": match["metadata"]["source"],
#         }
#         for match in results["matches"]
#     ]


# # Check index

# def index_exists() -> bool:
#     try:
#         PC =Pinecone(api_key=PINECONE_API_KEY)
#         existing = [i.name for i in PC.list_indexes()]
#         if INDEX_NAME not in existing:
#             return False
#         stats = PC.Index(INDEX_NAME).describe_index_stats()
#         return stats["total_vector_count"] > 0
#     except:
#         return False


import os
import hashlib
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz
import numpy as np
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "../.env.local"))

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX", "doc-rag-index")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Larger chunk size = fewer chunks = less embedding + upload time,
# with minimal retrieval quality loss for MiniLM's 256-token window.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1200))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 150))
TOP_K = int(os.getenv("TOP_K", 5))

EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", 64))
UPSERT_BATCH_SIZE = int(os.getenv("UPSERT_BATCH_SIZE", 200))
UPSERT_MAX_WORKERS = int(os.getenv("UPSERT_MAX_WORKERS", 8))

CACHE_PATH = os.path.join(BASE_DIR, "embeddings_cache.pkl")

_model = None


# Embedding model

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[Embeddings] Loading model: {EMBEDDING_MODEL}", flush=True)
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


# Pinecone

def get_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing = [i.name for i in pc.list_indexes()]

    if INDEX_NAME not in existing:
        print(f"[Pinecone] Creating index: {INDEX_NAME}", flush=True)
        pc.create_index(
            name=INDEX_NAME,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print("[Pinecone] Index created", flush=True)

    return pc.Index(INDEX_NAME)


# Extract text

def extract_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page_num, page in enumerate(doc):
        full_text += f"\n--- Page {page_num + 1} ---\n"
        full_text += page.get_text()
    doc.close()
    return full_text


# Chunk text

def chunk_text(text: str) -> list:
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


# Stable, content-derived vector ID so re-running ingestion overwrites
# the same chunk instead of colliding with an unrelated positional index.

def make_vector_id(source: str, text: str) -> str:
    digest = hashlib.md5(f"{source}::{text}".encode("utf-8")).hexdigest()
    return digest


# Embeddings with on-disk checkpointing so a crash mid-run doesn't cost
# the full embedding pass again.

def embed_chunks(all_chunks: list) -> np.ndarray:
    texts = [c["text"] for c in all_chunks]

    if os.path.exists(CACHE_PATH):
        print(f"[Embeddings] Loading cached embeddings from {CACHE_PATH}", flush=True)
        with open(CACHE_PATH, "rb") as f:
            cached = pickle.load(f)
        if len(cached) == len(texts):
            return cached
        print("[Embeddings] Cache size mismatch, re-embedding", flush=True)

    model = get_model()
    print(f"\n[Embeddings] Total chunks: {len(texts)}", flush=True)
    print("[Embeddings] Creating embeddings...", flush=True)

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=EMBED_BATCH_SIZE,
    )

    with open(CACHE_PATH, "wb") as f:
        pickle.dump(embeddings, f)

    return embeddings


# Parallel Pinecone upsert

def upsert_batch(index, vectors: list):
    index.upsert(vectors=vectors)


def upload_vectors(index, all_chunks: list, embeddings: np.ndarray):
    print("[Pinecone] Uploading vectors...", flush=True)

    batches = []
    for i in range(0, len(all_chunks), UPSERT_BATCH_SIZE):
        batch_chunks = all_chunks[i:i + UPSERT_BATCH_SIZE]
        batch_embeds = embeddings[i:i + UPSERT_BATCH_SIZE]
        vectors = [
            {
                "id": make_vector_id(chunk["source"], chunk["text"]),
                "values": emb.tolist(),
                "metadata": {
                    "text": chunk["text"],
                    "source": chunk["source"],
                },
            }
            for chunk, emb in zip(batch_chunks, batch_embeds)
        ]
        batches.append(vectors)

    with ThreadPoolExecutor(max_workers=UPSERT_MAX_WORKERS) as executor:
        futures = [executor.submit(upsert_batch, index, b) for b in batches]
        for n, future in enumerate(as_completed(futures), 1):
            future.result()
            print(f"[Pinecone] Batch {n}/{len(batches)} done", flush=True)

    print(f"[Pinecone] Done - {len(all_chunks)} vectors stored", flush=True)


# Build Index

def build_index(pdf_files: list) -> tuple:
    all_chunks = []

    for pdf in pdf_files:
        print(f"[Chunking] {pdf['name']}", flush=True)
        text = extract_text(pdf["bytes"])
        chunks = chunk_text(text)
        print(f" -> {len(chunks)} chunks", flush=True)
        for chunk in chunks:
            all_chunks.append({
                "text": chunk,
                "source": pdf["name"],
            })

    embeddings = embed_chunks(all_chunks)
    index = get_pinecone_index()
    upload_vectors(index, all_chunks, embeddings)

    return index, all_chunks


# Search similar chunks

def search(query: str, top_k: int = TOP_K) -> list:
    model = get_model()
    index = get_pinecone_index()
    query_vec = model.encode([query])[0].tolist()

    results = index.query(vector=query_vec, top_k=top_k, include_metadata=True)

    return [
        {
            "text": match["metadata"]["text"],
            "source": match["metadata"]["source"],
        }
        for match in results["matches"]
    ]


# Check index

def index_exists() -> bool:
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        existing = [i.name for i in pc.list_indexes()]
        if INDEX_NAME not in existing:
            return False
        stats = pc.Index(INDEX_NAME).describe_index_stats()
        return stats["total_vector_count"] > 0
    except Exception:
        return False