from __future__ import annotations

from typing import Any

from . import settings
from .embeddings import embed_text
from .qdrant_store import search


def _format_hit(hit: dict[str, Any]) -> str:
    payload = hit.get("payload") or {}
    title = payload.get("title") or payload.get("source") or "Knowledge"
    doc_type = payload.get("doc_type") or "document"
    ticker = payload.get("ticker")
    score = hit.get("score")
    header = f"[{doc_type}"
    if ticker:
        header += f":{ticker}"
    if score is not None:
        header += f" score={score:.3f}"
    header += f"] {title}"
    return f"{header}\n{payload.get('text', '').strip()}"


def retrieve_context(
    query: str,
    *,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
) -> str:
    if not settings.RAG_ENABLED:
        return ""
    if not query.strip():
        return ""

    try:
        vector = embed_text(query)
        hits = search(vector, top_k or settings.RAG_TOP_K, filters=filters)
    except Exception:
        return ""

    snippets = [_format_hit(hit) for hit in hits if (hit.get("payload") or {}).get("text")]
    return "\n\n---\n\n".join(snippets)
