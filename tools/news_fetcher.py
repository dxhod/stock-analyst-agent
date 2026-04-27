"""
Tool: recent news via Financial Modeling Prep API
"""

import os
import requests
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("FMP_API_KEY")
BASE = "https://financialmodelingprep.com/api/v3"


def _days_ago(date_str: str) -> int | None:
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_news(ticker: str, max_items: int = 10) -> list[dict]:
    params = {"tickers": ticker.upper(), "limit": max_items, "apikey": API_KEY}
    r = requests.get(f"{BASE}/stock_news", params=params, timeout=10)
    r.raise_for_status()
    raw = r.json()

    results = []
    for item in raw:
        date_str = (item.get("publishedDate") or "")[:10]
        results.append({
            "title": item.get("title", "").strip(),
            "date": date_str,
            "days_ago": _days_ago(date_str),
            "source": item.get("site", "unknown"),
            "summary": (item.get("text") or "")[:400],
            "url": item.get("url", ""),
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
