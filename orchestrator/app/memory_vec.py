from __future__ import annotations

import os
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Local, persistent DB under repo folder
_DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".chroma"))
os.makedirs(_DB_DIR, exist_ok=True)

# Singletons (simple module-scope cache)
_client: chromadb.Client | None = None
_model: SentenceTransformer | None = None
_COLLECTION_NAME = "mcp_mem_v1"


def get_client() -> chromadb.Client:
    global _client
    if _client is None:
        _client = chromadb.Client(
            Settings(
                persist_directory=_DB_DIR,
                is_persistent=True,
            )
        )
    return _client


def get_model(name: str = "sentence-transformers/all-MiniLM-L6-v2") -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(name)
    return _model


def _embeddings(texts: list[str]) -> list[list[float]]:
    model = get_model()
    # normalize_embeddings in Chroma handles cosine, we just provide vectors
    vecs = model.encode(texts, normalize_embeddings=True).tolist()
    return vecs


def _collection():
    cli = get_client()
    if _COLLECTION_NAME not in [c.name for c in cli.list_collections()]:
        return cli.create_collection(name=_COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    return cli.get_collection(_COLLECTION_NAME)


def add_memory(text: str, kind: str = "note", metadata: dict[str, Any] | None = None) -> str:
    """
    Adds a single memory item; returns the generated id.
    """
    col = _collection()
    doc_id = f"m_{col.count() + 1}"
    col.add(
        ids=[doc_id],
        documents=[text],
        metadatas=[{"kind": kind, **(metadata or {})}],
        embeddings=_embeddings([text]),
    )
    return doc_id


def query_memory(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    col = _collection()
    res = col.query(
        query_embeddings=_embeddings([query]),
        n_results=top_k,
        include=["documents", "metadatas", "distances"],  # <- "ids" entfernt
    )
    out: list[dict[str, Any]] = []
    # ids sind trotzdem in res enthalten
    for i in range(len(res["ids"][0])):
        out.append(
            {
                "id": res["ids"][0][i],
                "text": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
                "distance": res["distances"][0][i],
            }
        )
    return out
