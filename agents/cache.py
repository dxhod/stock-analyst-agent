from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

CACHE_TTL = timedelta(minutes=30)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_valid_cached_analysis(cache: dict[str, Any] | None) -> dict[str, Any] | None:
    if not cache:
        return None

    created_at = cache.get("created_at")
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at)
        except ValueError:
            return None

    if not isinstance(created_at, datetime):
        return None

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    if now_utc() - created_at > CACHE_TTL:
        return None

    return cache


def build_analysis_cache(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at": now_utc(),
        "ticker": state.get("ticker"),
        "tickers": state.get("tickers") or ([state.get("ticker")] if state.get("ticker") else []),
        "language": state.get("language"),
        "user_query": state.get("user_query"),
        "technical_analysis": state.get("technical_analysis", ""),
        "fundamental_analysis": state.get("fundamental_analysis", ""),
        "news_analysis": state.get("news_analysis", ""),
        "analysis": state.get("analysis", ""),
    }
