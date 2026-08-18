from __future__ import annotations

import json
from typing import Any, Dict

import chromadb

from config import CHROMA_DB_DIR, COLLECTION_NAME


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            sanitized[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, (list, tuple, dict)):
            sanitized[key] = json.dumps(value, ensure_ascii=False)
        else:
            sanitized[key] = str(value)
    return sanitized


def get_collection() -> Any:
    CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def get_collection_state(collection: Any) -> Dict[str, Dict[str, Any]]:
    response = collection.get(include=["metadatas"])
    state: Dict[str, Dict[str, Any]] = {}

    for index, metadata in enumerate(response.get("metadatas", []) or []):
        source = metadata.get("source") if metadata else None
        if not source:
            continue

        state.setdefault(source, {"ids": [], "hash": None})
        state[source]["ids"].append(response["ids"][index])
        if not state[source]["hash"] and metadata.get("file_hash"):
            state[source]["hash"] = metadata.get("file_hash")

    return state
