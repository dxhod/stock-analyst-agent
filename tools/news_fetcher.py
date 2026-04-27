"""
Tool: recent news via yfinance
"""

import yfinance as yf
from curl_cffi import requests as curl_requests
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential

yf.set_tz_cache_location("/tmp")
session = curl_requests.Session(impersonate="chrome")


def _days_ago(date_str: str) -> int | None:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return None


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=2, max=10))
def fetch_news(ticker: str, max_items: int = 10) -> list[dict]:
    tk = yf.Ticker(ticker.upper(), session=session)
    raw = tk.news or []

    results = []
    for item in raw[:max_items]:
        content = item.get("content", {})
        title = content.get("title", "").strip()
        if not title:
            continue
        pub = content.get("pubDate", "")
        date_str = pub[:10] if pub else ""
        results.append({
            "title": title,
            "date": date_str,
            "days_ago": _days_ago(date_str),
            "source": content.get("provider", {}).get("displayName", "unknown"),
            "summary": (content.get("summary") or "")[:400],
            "url": (content.get("canonicalUrl") or {}).get("url", ""),
        })

    results.sort(key=lambda x: x["days_ago"] if x["days_ago"] is not None else 9999)
    return results


def news_to_text(news_items: list[dict]) -> str:
    if not news_items:
        return "No recent news found."
    lines = []
    for item in news_items:
        age = f"{item['days_ago']}d ago" if item["days_ago"] is not None else item["date"]
        lines.append(f"[{age}] {item['source']}: {item['title']}")
        if item["summary"]:
            lines.append(f"  {item['summary'][:200]}")
    return "\n".join(lines)
