"""
Vector Memory — skeleton.
Wraps Chroma/FAISS for semantic retrieval.
"""

from typing import Any

_MEMORY: list[dict[str, Any]] = []


def add_memory(text: str, kind: str = "note") -> None:
    _MEMORY.append({"text": text, "kind": kind})


def query_memory(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    res = [m for m in _MEMORY if query.lower() in m["text"].lower()]
    return res[:top_k]
