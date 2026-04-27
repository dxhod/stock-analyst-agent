"""
Tool: price & OHLCV data via Financial Modeling Prep API
"""

import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("FMP_API_KEY")
BASE = "https://financialmodelingprep.com/api/v3"


def _get(endpoint: str, params: dict = {}) -> dict | list:
    params["apikey"] = API_KEY
    r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def _sma(prices: list[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 4)


def _rsi(prices: list[float], period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d for d in deltas[-period:] if d > 0]
    losses = [-d for d in deltas[-period:] if d < 0]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_price_data(ticker: str, period: str = "6mo") -> dict:
    # Historical prices
    data = _get(f"historical-price-full/{ticker.upper()}", {"serietype": "line", "timeseries": 200})
    history = data.get("historical", [])

    if not history:
        raise ValueError(f"No price data found for '{ticker}'")

    closes = [d["close"] for d in reversed(history)]
    current_price = closes[-1]
    prev_close = closes[-2]
    change_pct = (current_price - prev_close) / prev_close * 100

    high_52w = max(d["close"] for d in history[:252])
    low_52w = min(d["close"] for d in history[:252])

    # Volume from full OHLCV
    ohlcv = _get(f"historical-price-full/{ticker.upper()}", {"timeseries": 30})
    ohlcv_hist = ohlcv.get("historical", [])
    volumes = [d["volume"] for d in ohlcv_hist]
    avg_volume = int(sum(volumes) / len(volumes)) if volumes else 0
    rel_volume = round(volumes[0] / avg_volume, 2) if avg_volume else None

    sma_20 = _sma(closes, 20)
    sma_50 = _sma(closes, 50)
    sma_200 = _sma(closes, 200)

    cross_signal = None
    if sma_50 and sma_200:
        cross_signal = "golden_cross" if sma_50 > sma_200 else "dead_cross"

    return {
        "ticker": ticker.upper(),
        "current_price": round(current_price, 4),
        "prev_close": round(prev_close, 4),
        "change_pct": round(change_pct, 2),
        "high_52w": round(high_52w, 4),
        "low_52w": round(low_52w, 4),
        "pct_from_52w_high": round((current_price - high_52w) / high_52w * 100, 2),
        "sma_20": sma_20,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "cross_signal": cross_signal,
        "rsi_14": _rsi(closes),
        "atr_14": None,
        "volume_today": volumes[0] if volumes else None,
        "avg_volume_30d": avg_volume,
        "relative_volume": rel_volume,
        "data_period": period,
        "bars_count": len(closes),
    }
