from __future__ import annotations

import requests

from . import settings


class EmbeddingError(RuntimeError):
    pass


def embed_text(text: str) -> list[float]:
    if not settings.GEMINI_API_KEY:
        raise EmbeddingError("GEMINI_API_KEY is not configured.")

    model = settings.GEMINI_EMBEDDING_MODEL
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:embedContent?key={settings.GEMINI_API_KEY}"
    )
    body = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": settings.GEMINI_EMBEDDING_DIMENSIONS,
    }
    response = requests.post(url, json=body, timeout=30)
    if response.status_code >= 400:
        raise EmbeddingError(f"Gemini embedding failed: {response.status_code} {response.text[:400]}")

    data = response.json()
    values = (data.get("embedding") or {}).get("values")
    if not values:
        raise EmbeddingError("Gemini embedding response did not include embedding values.")
    return [float(value) for value in values]
