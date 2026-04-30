from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    user_query: str
    ticker: str
    tickers: list[str]
    language: str
    intent: dict[str, Any]
    conversation: list[dict[str, str]]
    cached_analysis: dict[str, Any] | None
    price_data: dict[str, Any]
    price_data_by_ticker: dict[str, dict[str, Any]]
    fundamentals: dict[str, Any]
    fundamentals_by_ticker: dict[str, dict[str, Any]]
    news: list[dict]
    news_by_ticker: dict[str, list[dict]]
    technical_analysis: str
    fundamental_analysis: str
    news_analysis: str
    analysis: str
    error: str | None
