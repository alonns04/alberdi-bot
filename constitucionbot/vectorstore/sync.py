from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from config import MANIFEST_PATH
from ingestion.hashing import compute_file_hash
from vectorstore.chroma_client import get_collection, get_collection_state


def load_sync_manifest() -> Dict[str, Any]:
    if MANIFEST_PATH.exists():
        try:
            with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"documents": {}, "runs": []}


def save_sync_manifest(data: Dict[str, Any]) -> None:
    MANIFEST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def compare_documents(current_sources: Set[str], manifest: Dict[str, Any], existing_state: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    documents = manifest.get("documents", {}) or {}
    changed_documents: List[Dict[str, Any]] = []
    unchanged_documents: List[Dict[str, Any]] = []
    removed_documents: List[Dict[str, Any]] = []

    for source in sorted(current_sources):
        previous_entry = documents.get(source)
        if previous_entry and previous_entry.get("hash"):
            unchanged_documents.append({"source": source, "hash": previous_entry["hash"]})
        else:
            changed_documents.append({"source": source})

    for source in sorted(documents.keys()):
        if source not in current_sources:
            removed_documents.append({"source": source, **documents[source]})

    return changed_documents, unchanged_documents, removed_documents


def get_pending_documents(paths: List[Path], manifest: Dict[str, Any], existing_state: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    current_sources = {str(path.relative_to(Path(__file__).resolve().parent.parent).replace("\\", "/")) for path in paths}
    return compare_documents(current_sources, manifest, existing_state)
