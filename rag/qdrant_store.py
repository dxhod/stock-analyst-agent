from __future__ import annotations

from typing import Any

import requests

from . import settings


class QdrantError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.QDRANT_API_KEY:
        headers["api-key"] = settings.QDRANT_API_KEY
    return headers


def _url(path: str) -> str:
    if not settings.QDRANT_URL:
        raise QdrantError("QDRANT_URL is not configured.")
    return f"{settings.QDRANT_URL}{path}"


def ensure_collection() -> None:
    body = {
        "vectors": {
            "size": settings.GEMINI_EMBEDDING_DIMENSIONS,
            "distance": "Cosine",
        }
    }
    response = requests.put(
        _url(f"/collections/{settings.QDRANT_COLLECTION}"),
        headers=_headers(),
        json=body,
        timeout=30,
    )
    if response.status_code >= 400:
        raise QdrantError(f"Qdrant collection setup failed: {response.status_code} {response.text[:400]}")


def upsert_points(points: list[dict[str, Any]]) -> None:
    if not points:
        return
    body = {"points": points}
    response = requests.put(
        _url(f"/collections/{settings.QDRANT_COLLECTION}/points?wait=true"),
        headers=_headers(),
        json=body,
        timeout=60,
    )
    if response.status_code >= 400:
        raise QdrantError(f"Qdrant upsert failed: {response.status_code} {response.text[:400]}")


def search(vector: list[float], top_k: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "vector": vector,
        "limit": top_k,
        "with_payload": True,
    }
    if filters:
        body["filter"] = {
            "must": [
                {"key": key, "match": {"value": value}}
                for key, value in filters.items()
                if value not in (None, "", [])
            ]
        }

    response = requests.post(
        _url(f"/collections/{settings.QDRANT_COLLECTION}/points/search"),
        headers=_headers(),
        json=body,
        timeout=30,
    )
    if response.status_code >= 400:
        raise QdrantError(f"Qdrant search failed: {response.status_code} {response.text[:400]}")
    return response.json().get("result", [])
