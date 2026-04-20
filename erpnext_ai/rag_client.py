import os
import requests

RAG_URL = os.getenv("TRITECH_RAG_URL", "http://172.16.19.215:8000").rstrip("/")


def rag_health(timeout: int = 5):
    try:
        r = requests.get(f"{RAG_URL}/health", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"status": "offline", "error": str(e)}


def rag_chat(message: str, erp_url: str, session_id: str, timeout: int = 120):
    """
    POST to FastAPI /chat.
    erp_url    — tells the agent which ERP credentials to use
    session_id — isolates conversation history per user per site
    """
    r = requests.post(
        f"{RAG_URL}/chat",
        json={
            "query":      message,
            "erp_url":    erp_url,
            "session_id": session_id,
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()
