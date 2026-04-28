from typing import TypedDict, Any

class AgentState(TypedDict):
    ticker: str
    language: str
    price_data: dict[str, Any]
    fundamentals: dict[str, Any]
    news: list[dict]
    analysis: str
    error: str | None
