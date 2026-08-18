from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from dataclasses import dataclass

from config import EMBEDDING_MODEL, RAG_CONTEXT_NEIGHBORS, RAG_TOP_K, ROOT_DIR
from ingestion.discover import discover_documents
from ingestion.embeddings import create_embeddings
from ingestion.extractor import extract_documents
from ingestion.chunker import normalize_article
from ingestion.hashing import compute_file_hash
from vectorstore.chroma_client import get_collection, get_collection_state, sanitize_metadata
from vectorstore.sync import load_sync_manifest, save_sync_manifest


def get_relative_source(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR)).replace("\\", "/")


def _normalize_text_for_filter(text: str | None) -> str:
    if not text:
        return ""
    normalized = text.lower()
    normalized = normalized.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


@dataclass
class QueryConstraints:
    article: str | None = None
    chapter: str | None = None
    section: str | None = None
    norm_category: str | None = None
    document_name: str | None = None
    strict_source: bool = False


def _parse_query_constraints(query: str | None, collection: Any) -> QueryConstraints:
    if not query:
        return QueryConstraints()

    constraints = QueryConstraints()
    normalized_query = _normalize_text_for_filter(query)

    article_match = re.search(
        r"\bart(?:[íi]culo)?\.?\s*(?:n(?:º|ro|°)?\.?\s*)?(\d+[a-z]?(?:\s*bis)?)",
        query,
        re.IGNORECASE,
    )
    if article_match:
        constraints.article = normalize_article(article_match.group(1))

    chapter_match = re.search(r"\bcap(?:í|i)tulo\s+([IVXLCDM\d]+)", query, re.IGNORECASE)
    if chapter_match:
        constraints.chapter = chapter_match.group(1).strip().upper()

    section_match = re.search(r"\bsecci(?:ó|o)n\s+([0-9]+(?:[a-z])?)", query, re.IGNORECASE)
    if section_match:
        constraints.section = section_match.group(1).strip()

    if "constituci" in normalized_query and (
        "nacional" in normalized_query or "nacion argentina" in normalized_query or " cn " in f" {normalized_query} "
    ):
        constraints.norm_category = "constitucion_nacional"
        constraints.strict_source = True

    if "codigo penal" in normalized_query and "procesal" not in normalized_query:
        constraints.norm_category = "codigo_penal"
        constraints.strict_source = True
    elif "codigo procesal penal" in normalized_query or "procesal penal" in normalized_query:
        constraints.norm_category = "codigo_procesal_penal"
        constraints.strict_source = True

    document_filter = _match_document_filter(query, collection, preferred_norm=constraints.norm_category)
    if document_filter:
        constraints.document_name = document_filter.get("document_name")
        if constraints.norm_category or constraints.article:
            constraints.strict_source = True

    return constraints


def _document_hints_from_query(query: str) -> List[str]:
    normalized_query = _normalize_text_for_filter(query)
    hints: List[str] = []
    hint_rules = [
        ("constituci", "constituc"),
        ("codigo procesal penal", "procesal penal"),
        ("codigo penal", "codigo penal"),
        ("derecho penal", "derecho penal"),
        ("manual de la constitucion", "manual de la constitucion"),
        ("lectura facil", "lectura facil"),
    ]
    for trigger, hint in hint_rules:
        if trigger in normalized_query:
            hints.append(hint)
    return hints


def _match_document_filter(query: str, collection: Any) -> Dict[str, Any] | None:
    normalized_query = _normalize_text_for_filter(query)
    hints = _document_hints_from_query(query)

    try:
        response = collection.get(include=["metadatas"], limit=5000)
    except Exception:
        return None

    candidates: List[Tuple[int, str]] = []
    for metadata in response.get("metadatas", []) or []:
        if not metadata:
            continue
        document_name = metadata.get("document_name") or ""
        normalized_name = _normalize_text_for_filter(document_name)
        if not normalized_name:
            continue

        score = 0
        if normalized_name in normalized_query or normalized_query in normalized_name:
            score += 3
        for hint in hints:
            if hint in normalized_name:
                score += 2
        for field in ("book", "title", "source"):
            normalized_field = _normalize_text_for_filter(metadata.get(field))
            for hint in hints:
                if hint in normalized_field:
                    score += 1

        if score:
            candidates.append((score, document_name))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return {"document_name": candidates[0][1]}


def _infer_metadata_filters(query: str | None, collection: Any) -> Dict[str, Any] | None:
    if not query:
        return None

    filters: List[Dict[str, Any]] = []

    article_match = re.search(
        r"\bart(?:[íi]culo)?\.?\s*(?:n(?:º|ro|°)?\.?\s*)?(\d+[a-z]?(?:\s*bis)?)",
        query,
        re.IGNORECASE,
    )
    if article_match:
        normalized_article = normalize_article(article_match.group(1))
        if normalized_article:
            filters.append({"article": normalized_article})

    chapter_match = re.search(r"\bcap(?:í|i)tulo\s+([IVXLCDM\d]+)", query, re.IGNORECASE)
    if chapter_match:
        filters.append({"chapter": chapter_match.group(1).strip().upper()})

    section_match = re.search(r"\bsecci(?:ó|o)n\s+([0-9]+(?:[a-z])?)", query, re.IGNORECASE)
    if section_match:
        filters.append({"section": section_match.group(1).strip()})

    document_filter = _match_document_filter(query, collection)
    if document_filter:
        filters.append(document_filter)

    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}


def _result_from_hit(metadata: Dict[str, Any], content: str, score: float | None = None) -> Dict[str, Any]:
    return {
        "score": score,
        "source": metadata.get("source", ""),
        "type": metadata.get("type", ""),
        "document_type": metadata.get("document_type", metadata.get("type", "")),
        "document_name": metadata.get("document_name", ""),
        "book": metadata.get("book", ""),
        "title": metadata.get("title", ""),
        "chapter": metadata.get("chapter", ""),
        "section": metadata.get("section", ""),
        "article": metadata.get("article", ""),
        "inciso": metadata.get("inciso", ""),
        "page": metadata.get("page"),
        "chunk_index": metadata.get("chunk_index"),
        "file_hash": metadata.get("file_hash", ""),
        "content": content,
    }


def _get_neighbor_chunks(
    collection: Any,
    source: str,
    chunk_index: int | None,
    radius: int = RAG_CONTEXT_NEIGHBORS,
) -> List[Dict[str, Any]]:
    if not source or chunk_index is None or radius <= 0:
        return []

    try:
        response = collection.get(where={"source": source}, include=["documents", "metadatas"], limit=5000)
    except Exception:
        return []

    neighbors: List[Dict[str, Any]] = []
    documents = response.get("documents", []) or []
    metadatas = response.get("metadatas", []) or []

    for index, metadata in enumerate(metadatas):
        if not metadata:
            continue
        sibling_index = metadata.get("chunk_index")
        if sibling_index is None:
            continue
        try:
            sibling_index_int = int(sibling_index)
            chunk_index_int = int(chunk_index)
        except (TypeError, ValueError):
            continue
        if abs(sibling_index_int - chunk_index_int) > radius:
            continue
        content = documents[index] if index < len(documents) else ""
        neighbors.append(_result_from_hit(metadata, content))

    neighbors.sort(key=lambda item: (item.get("chunk_index") if item.get("chunk_index") is not None else -1))
    return neighbors


def _expand_with_neighbors(collection: Any, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    expanded: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, Any]] = set()

    for hit in hits:
        metadata_key = (hit.get("source", ""), hit.get("chunk_index"))
        if metadata_key not in seen:
            expanded.append(hit)
            seen.add(metadata_key)

        for neighbor in _get_neighbor_chunks(collection, hit.get("source", ""), hit.get("chunk_index")):
            neighbor_key = (neighbor.get("source", ""), neighbor.get("chunk_index"))
            if neighbor_key in seen:
                continue
            expanded.append(neighbor)
            seen.add(neighbor_key)

    return expanded


def _run_vector_query(
    collection: Any,
    embedding_list: List[List[float]],
    top_k: int,
    metadata_filters: Dict[str, Any] | None,
) -> List[Dict[str, Any]]:
    n_results = min(max(top_k, 3), 25)
    query_kwargs: Dict[str, Any] = {
        "query_embeddings": embedding_list,
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if metadata_filters:
        query_kwargs["where"] = metadata_filters

    results = collection.query(**query_kwargs)
    documents = results.get("documents", [[]])[0]
    if not documents and metadata_filters:
        results = collection.query(
            query_embeddings=embedding_list,
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    output: List[Dict[str, Any]] = []
    for index in range(len(results.get("documents", [[]])[0])):
        metadata = results["metadatas"][0][index] or {}
        output.append(
            _result_from_hit(
                metadata,
                results["documents"][0][index],
                float(results["distances"][0][index]),
            )
        )
    return output


def build_vector_db(model_name: str = EMBEDDING_MODEL) -> Dict[str, Any]:
    collection = get_collection()
    manifest = load_sync_manifest()
    existing_state = get_collection_state(collection)
    documents_paths = discover_documents()
    current_sources = {get_relative_source(path) for path in documents_paths}

    processed_chunks = 0
    skipped_documents = 0
    removed_documents = 0
    run_timestamp = datetime.now(timezone.utc).isoformat()
    run_summary: List[Dict[str, Any]] = []

    for path in documents_paths:
        source = get_relative_source(path)
        file_hash = compute_file_hash(path)
        previous_state = existing_state.get(source)
        previous_entry = (manifest.get("documents", {}) or {}).get(source)

        if previous_entry and previous_entry.get("hash") == file_hash:
            skipped_documents += 1
            run_summary.append(
                {
                    "source": source,
                    "name": path.name,
                    "status": "skipped",
                    "hash": file_hash,
                    "chunks": previous_entry.get("chunks", 0),
                    "updated_at": run_timestamp,
                }
            )
            continue

        ids_to_remove = []
        if previous_entry and previous_entry.get("ids"):
            ids_to_remove = previous_entry["ids"]
        elif previous_state and previous_state.get("ids"):
            ids_to_remove = previous_state["ids"]

        if ids_to_remove:
            collection.delete(ids=ids_to_remove)

        documents = extract_documents(path)
        if not documents:
            continue

        texts = [item["content"] for item in documents]
        embeddings = create_embeddings(texts, model_name=model_name)

        ids: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        for index, item in enumerate(documents):
            safe_source = re.sub(r"[^a-zA-Z0-9._-]", "_", item["source"])
            ids.append(f"{safe_source}-{index}-{uuid.uuid4().hex[:8]}")
            metadata = {
                "source": item.get("source", ""),
                "type": item.get("type", ""),
                "document_type": item.get("document_type", item.get("type", "")),
                "chunk_index": index,
                "file_hash": file_hash,
                "file_name": path.name,
                "document_name": item.get("document_name", path.name),
                "book": item.get("book", ""),
                "title": item.get("title", ""),
                "chapter": item.get("chapter", ""),
                "section": item.get("section", ""),
                "article": normalize_article(item.get("article")) or item.get("article", ""),
                "inciso": item.get("inciso", ""),
                "page": item.get("page"),
            }
            metadatas.append(sanitize_metadata(metadata))

        collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
        )
        processed_chunks += len(documents)
        run_summary.append(
            {
                "source": source,
                "name": path.name,
                "status": "processed",
                "hash": file_hash,
                "chunks": len(documents),
                "updated_at": run_timestamp,
            }
        )

    for old_source, state in (manifest.get("documents", {}) or {}).items():
        if old_source not in current_sources:
            ids_to_remove = state.get("ids", [])
            if ids_to_remove:
                collection.delete(ids=ids_to_remove)
            removed_documents += 1
            run_summary.append(
                {
                    "source": old_source,
                    "name": state.get("name", old_source),
                    "status": "removed",
                    "hash": state.get("hash"),
                    "chunks": state.get("chunks", 0),
                    "updated_at": run_timestamp,
                }
            )

    current_state = get_collection_state(collection)
    updated_documents: Dict[str, Dict[str, Any]] = {}
    for source in sorted(current_sources):
        previous_entry = (manifest.get("documents", {}) or {}).get(source)
        entry = next((item for item in run_summary if item["source"] == source), None)
        state_ids = current_state.get(source, {}).get("ids", [])
        updated_documents[source] = {
            "source": source,
            "name": entry["name"] if entry else previous_entry.get("name", source.split("/")[-1]) if previous_entry else source.split("/")[-1],
            "hash": entry["hash"] if entry else previous_entry.get("hash") if previous_entry else None,
            "chunks": entry["chunks"] if entry else previous_entry.get("chunks", 0) if previous_entry else 0,
            "status": entry["status"] if entry else "skipped",
            "updated_at": entry["updated_at"] if entry else previous_entry.get("updated_at", run_timestamp) if previous_entry else run_timestamp,
            "ids": state_ids,
        }

    manifest_data = {
        "documents": updated_documents,
        "runs": [
            {
                "timestamp": run_timestamp,
                "processed_chunks": processed_chunks,
                "skipped_documents": skipped_documents,
                "removed_documents": removed_documents,
                "documents": [
                    {
                        "source": entry["source"],
                        "name": entry["name"],
                        "status": entry["status"],
                        "chunks": entry["chunks"],
                    }
                    for entry in run_summary
                ],
            },
            *manifest.get("runs", []),
        ][:10],
    }
    # Se conserva el código por si se vuelve a necesitar la sincronización:
    # save_sync_manifest(manifest_data)

    return {
        "documents_count": collection.count(),
        "processed_chunks": processed_chunks,
        "skipped_documents": skipped_documents,
        "removed_documents": removed_documents,
        "collection_name": "documentos",
        "storage_path": str(ROOT_DIR / "base" / "chroma_db"),
        "manifest_path": str(ROOT_DIR / "base" / "vector_sync_manifest.json"),
    }


def query_vector_db(query: str | None = None, top_k: int = RAG_TOP_K, query_embedding: Any = None) -> List[Dict[str, Any]]:
    collection = get_collection()
    if query_embedding is None:
        if not query:
            return []
        query_embedding = create_embeddings([query], model_name=EMBEDDING_MODEL)

    if hasattr(query_embedding, "tolist"):
        embedding_list = query_embedding.tolist()
    else:
        embedding_list = query_embedding

    if isinstance(embedding_list, list) and embedding_list and not isinstance(embedding_list[0], list):
        embedding_list = [embedding_list]

    metadata_filters = _infer_metadata_filters(query, collection)
    primary_hits = _run_vector_query(collection, embedding_list, top_k=top_k, metadata_filters=metadata_filters)
    return _expand_with_neighbors(collection, primary_hits)
