import os
import fitz
import numpy as np
from pinecone import Pinecone, ServerlessSpec
import requests
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "../.env.local"))

PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
INDEX_NAME= os.getenv("PINECONE_INDEX", "doc-rag-index")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1200))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 150))
TOP_K = int(os.getenv("TOP_K", 5))


# _model = None

HF_API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/{EMBEDDING_MODEL}"

#Embedding model

# def get_model() -> SentenceTransformer:
#     global _model
#     if _model is None:
#         print(f"[Embeddings] Loading model: {EMBEDDING_MODEL}", flush=True)
#         _model = SentenceTransformer(EMBEDDING_MODEL)
#     return _model

#get embedding model from huggingface api
def get_embedding(text: str) -> list:
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    response = requests.post(HF_API_URL, headers=headers, json={"inputs": text, "options": {"wait_for_model": True}})
    response.raise_for_status()
    embedding = response.json()

    if isinstance(embedding[0], list):
        embedding = embedding[0]
    
    return embedding

#get embedding for multiple texts
def get_embeddings_batch(texts: list) ->list:
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    response = requests.post(HF_API_URL, headers=headers, json={"inputs": texts, "options": {"wait_for_model": True}})
    response.raise_for_status()
    return response.json()


#Pinecone 

def get_pinecone_index():
    PC = Pinecone(api_key=PINECONE_API_KEY)
    existing = [i.name for i in PC.list_indexes()]

    if INDEX_NAME not in existing:
        print(f"[Pinecone] Creating index: {INDEX_NAME}", flush=True)
        PC.create_index(
            name=INDEX_NAME,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print("[Pinecone] Index created", flush=True)

    return PC.Index(INDEX_NAME)

#Extract text

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

#Build Index

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

#Build index with hugging face

def build_index(pdf_files: list) -> tuple:
    import time
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
    print(f"\n[Embeddings] Total chunks: {len(all_chunks)}", flush=True) 
    print("[Embeddings] Creating embeddings via Hugging Face API..", flush=True)

    index = get_pinecone_index()
    batch_size = 50

    for i in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[i:i + batch_size]
        texts = [c["text"] for c in batch_chunks]

        for attempt in range(3):
            try:
                embeddings = get_embeddings_batch(texts)
                break
            except Exception as e:
                print(f"[HF] Retry {attempt + 1}: {e}", flush=True)
                time.sleep(3)
        
        vectors = [
            {
                "id": str(i + j),
                "values": emb if isinstance(emb[0], float) else emb[0],
                "metadata": {
                    "text": chunk["text"],
                    "source": chunk["source"],
                }
            }
            for j, (chunk, emb) in enumerate(zip(batch_chunks, embeddings))
        ]

        #upload to pinecone
        for attempt in range(3):
            try:
                index.upsert(vectors=vectors)
                print(f"[Pinecone] Batch {i // batch_size + 1}", flush=True)
                break
            except Exception as e:
                print(f"[Pinecone] Retry {attempt + 1}: {e}", flush=True)
                time.sleep(2)

    print(f"[Pinecone] Done - {len(all_chunks)} vectors stored", flush=True)
    return index, all_chunks


# Search similar chunks

def search(query: str, top_k: int = TOP_K) -> list:
    # model = get_model()
    # index = get_pinecone_index()
    # query_vec = model.encode([query])[0].tolist()

    index = get_pinecone_index()
    query_vec = get_embedding(query)

    results = index.query(vector=query_vec, top_k=top_k, include_metadata=True)

    return [
        {
            "text": match["metadata"]["text"],
            "source": match["metadata"]["source"],
            "score": float(match["score"])
        }
        for match in results["matches"]
    ]


# Check index

def index_exists() -> bool:
    try:
        PC =Pinecone(api_key=PINECONE_API_KEY)
        existing = [i.name for i in PC.list_indexes()]
        if INDEX_NAME not in existing:
            return False
        stats = PC.Index(INDEX_NAME).describe_index_stats()
        return stats["total_vector_count"] > 0
    except:
        return False
