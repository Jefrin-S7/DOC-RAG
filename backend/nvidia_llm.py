import os
from openai import OpenAI
from dotenv import load_dotenv

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "../env.local"))

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta//llama-3.3-70b-instruct")

_client = None

def get_client():
    global _client
    if _client is None:
        if not NVIDIA_API_KEY:
            raise ValueError("NVIDIA_API_KEY not set in .env.local")
        _client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=NVIDIA_API_KEY
        )
    return _client


def build_prompt(question: str, chunks: list) -> str:
    context = "\n\n".join(f"[Source: {c['source']}]\n{c['text']}" for c in chunks)

    return f"""You are a helpful assistant. Answer using ONLY the context below.
IF the answer is not in the context, say "I could not find this in the documents."
Be concise and accurate.

Context:
{context}

Question: {question}

Answer:"""

def ask(question: str, relevant_chunks: list) -> dict:
    client = get_client()
    response = client.chat.completions.create(
        model=NVIDIA_MODEL,
        messages=[{"role": "user", "content": build_prompt(question, relevant_chunks)}],
        temperature=0.2,
        max_tokens=1024,
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": list({c["source"] for c in relevant_chunks}),
        "model": NVIDIA_MODEL,
        "tokens_used": response.usage.total_tokens,
    }