"""
Tool: recent news headlines
Fetches the latest news for a ticker via yfinance.
No API key required.
"""

from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential
import yfinance as yf
from curl_cffi import requests as curl_requests

yf.set_tz_cache_location("/tmp")
session = curl_requests.Session(impersonate="chrome")


def _parse_date(raw: str) -> str:
    """Parse ISO date string to YYYY-MM-DD, fallback gracefully."""
    if not raw:
        return "unknown"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return raw[:10] if len(raw) >= 10 else raw


def _days_ago(date_str: str) -> int | None:
    """Return how many days ago a YYYY-MM-DD date was."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return delta.days
    except Exception:
        return None


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=2, max=10))
def fetch_news(ticker: str, max_items: int = 10) -> list[dict]:
    """
    Return a list of recent news items for a ticker.

    Args:
        ticker:    Stock symbol, e.g. "AAPL"
        max_items: Maximum number of articles to return (default 10)

    Returns:
        List of dicts with keys: title, date, days_ago, source, summary, url
    """
    tk = yf.Ticker(ticker.upper(), session=session)
    raw_news = tk.news or []

    results = []
    for item in raw_news[:max_items]:
        content = item.get("content", {})

        title = content.get("title", "").strip()
        if not title:
            continue  # skip empty items

        date_str = _parse_date(content.get("pubDate", ""))
        provider = content.get("provider", {})

        results.append({
            "title": title,
            "date": date_str,
            "days_ago": _days_ago(date_str),
            "source": provider.get("displayName", "unknown"),
            "summary": (content.get("summary") or "").strip()[:400],
            "url": (content.get("canonicalUrl") or {}).get("url", ""),
        })

    # Sort by recency (most recent first, unknowns at the end)
    results.sort(key=lambda x: x["days_ago"] if x["days_ago"] is not None else 9999)

    return results


def news_to_text(news_items: list[dict]) -> str:
    """Format news list into a compact string for prompt injection."""
    if not news_items:
        return "No recent news found."
    lines = []
    for item in news_items:
        age = f"{item['days_ago']}d ago" if item["days_ago"] is not None else item["date"]
        lines.append(f"[{age}] {item['source']}: {item['title']}")
        if item["summary"]:
            lines.append(f"  {item['summary'][:200]}")
    return "\n".join(lines)
