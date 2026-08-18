from __future__ import annotations

from typing import Any, Dict, List

from config import RAG_TOP_K
from history.manager import append_interaction
from ingestion.embeddings import load_embedding_model
from llm.groq_client import ask
from vectorstore.indexer import query_vector_db


def _format_metadata_label(item: Dict[str, Any]) -> str:
    parts: List[str] = []
    if item.get("document_name"):
        parts.append(f"Documento: {item['document_name']}")
    if item.get("document_type"):
        parts.append(f"Tipo: {item['document_type']}")
    if item.get("book"):
        parts.append(f"Libro: {item['book']}")
    if item.get("title"):
        parts.append(f"Título: {item['title']}")
    if item.get("chapter"):
        parts.append(f"Capítulo: {item['chapter']}")
    if item.get("section"):
        parts.append(f"Sección: {item['section']}")
    if item.get("article"):
        parts.append(f"Artículo: {item['article']}")
    if item.get("inciso"):
        parts.append(f"Inciso: {item['inciso']}")
    if item.get("page"):
        parts.append(f"Página: {item['page']}")
    if item.get("chunk_index") is not None:
        parts.append(f"Fragmento: {item['chunk_index']}")
    return " | ".join(parts)


def format_reference(item: Dict[str, Any]) -> str:
    label = _format_metadata_label(item)
    excerpt = (item.get("content") or "").strip()
    if len(excerpt) > 180:
        excerpt = f"{excerpt[:177]}..."
    if label and excerpt:
        return f"{label}\n{excerpt}"
    return label or excerpt


def _build_context_from_results(results: List[Dict[str, Any]]) -> str:
    if not results:
        return ""

    blocks: List[str] = []
    for index, item in enumerate(results, start=1):
        label = _format_metadata_label(item)
        content = (item.get("content") or "").strip()
        if not content:
            continue
        blocks.append(f"--- Fragmento {index} ---\n{label}\n\n{content}")
    return "\n\n".join(blocks)


class ChatbotPipeline:
    def __init__(self) -> None:
        self.embedding_model = load_embedding_model()

    def retrieve(self, question: str, top_k: int = RAG_TOP_K) -> List[Dict[str, Any]]:
        embedding = self.embedding_model.encode(
            [question],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0]
        return query_vector_db(query=question, query_embedding=embedding, top_k=top_k)

    def _build_context(self, question: str, top_k: int = RAG_TOP_K) -> tuple[str, List[Dict[str, Any]]]:
        results = self.retrieve(question, top_k=top_k)
        return _build_context_from_results(results), results

    def process(
        self,
        question: str,
        user_id: str | None = None,
        api_key: str | None = None,
    ) -> Dict[str, Any]:
        context, results = self._build_context(question)
        references = [format_reference(item) for item in results if item.get("content")]
        answer = ask(question, context, user_id=user_id, api_key=api_key)
        append_interaction(question, answer, user_id=user_id)
        return {"answer": answer, "context": context, "references": references, "sources": results}
