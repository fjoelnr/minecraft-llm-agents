from __future__ import annotations

import os
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Persistent DB unter Repo-Root
_DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".chroma"))
os.makedirs(_DB_DIR, exist_ok=True)

_client: chromadb.Client | None = None
_model: SentenceTransformer | None = None

# Default-Collection-Name
DEFAULT_COLLECTION = "mem_general_v1"


def get_client() -> chromadb.Client:
    global _client
    if _client is None:
        _client = chromadb.Client(Settings(persist_directory=_DB_DIR, is_persistent=True))
    return _client


def get_model(name: str = "sentence-transformers/all-MiniLM-L6-v2") -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(name)
    return _model


def _embeddings(texts: list[str]) -> list[list[float]]:
    vecs = get_model().encode(texts, normalize_embeddings=True).tolist()
    return vecs


def _get_or_create_collection(name: str):
    cli = get_client()
    names = [c.name for c in cli.list_collections()]
    if name not in names:
        return cli.create_collection(name=name, metadata={"hnsw:space": "cosine"})
    return cli.get_collection(name)


def add_memory(
    text: str,
    kind: str = "note",
    metadata: dict[str, Any] | None = None,
    collection: str = DEFAULT_COLLECTION,
) -> str:
    col = _get_or_create_collection(collection)
    doc_id = f"{collection}__{col.count() + 1}"
    col.add(
        ids=[doc_id],
        documents=[text],
        metadatas=[{"kind": kind, **(metadata or {})}],
        embeddings=_embeddings([text]),
    )
    return doc_id


def add_batch(
    texts: list[str],
    kind: str = "note",
    metadatas: list[dict[str, Any]] | None = None,
    collection: str = DEFAULT_COLLECTION,
) -> list[str]:
    if not texts:
        return []
    col = _get_or_create_collection(collection)
    base = col.count()
    ids = [f"{collection}__{base + i + 1}" for i in range(len(texts))]
    md = metadatas if metadatas is not None else [{"kind": kind} for _ in texts]
    col.add(ids=ids, documents=texts, metadatas=md, embeddings=_embeddings(texts))
    return ids


def query_memory(
    query: str, top_k: int = 3, collection: str = DEFAULT_COLLECTION
) -> list[dict[str, Any]]:
    col = _get_or_create_collection(collection)
    res = col.query(
        query_embeddings=_embeddings([query]),
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    out: list[dict[str, Any]] = []
    for i in range(len(res["documents"][0])):
        out.append(
            {
                "id": res["ids"][0][i],
                "text": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
                "distance": res["distances"][0][i],
            }
        )
    return out


def stats(collection: str = DEFAULT_COLLECTION) -> dict[str, Any]:
    col = _get_or_create_collection(collection)
    return {"collection": collection, "count": col.count(), "persist_dir": _DB_DIR}


def drop_collection(collection: str) -> bool:
    get_client().delete_collection(collection)
    return True


def list_collections() -> list[str]:
    return [c.name for c in get_client().list_collections()]
