"""
Tool: price & OHLCV data via yfinance
"""

import yfinance as yf
from curl_cffi import requests as curl_requests
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

yf.set_tz_cache_location("/tmp")
session = curl_requests.Session(impersonate="chrome")


def _sma(series: pd.Series, period: int) -> float | None:
    if len(series) < period:
        return None
    return round(float(series.rolling(period).mean().iloc[-1]), 4)


def _rsi(series: pd.Series, period: int = 14) -> float | None:
    if len(series) < period + 1:
        return None
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss
    return round(float((100 - (100 / (1 + rs))).iloc[-1]), 2)


def _atr(hist: pd.DataFrame, period: int = 14) -> float | None:
    if len(hist) < period + 1:
        return None
    high, low, close = hist["High"], hist["Low"], hist["Close"]
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    return round(float(tr.rolling(period).mean().iloc[-1]), 4)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=2, max=10))
def fetch_price_data(ticker: str, period: str = "6mo") -> dict:
    tk = yf.Ticker(ticker.upper(), session=session)
    hist = tk.history(period=period)

    if hist.empty:
        raise ValueError(f"No price data for '{ticker}'")

    close = hist["Close"]
    volume = hist["Volume"]

    current_price = float(close.iloc[-1])
    prev_close = float(close.iloc[-2])
    change_pct = (current_price - prev_close) / prev_close * 100

    hist_1y = tk.history(period="1y")
    high_52w = float(hist_1y["High"].max()) if not hist_1y.empty else None
    low_52w = float(hist_1y["Low"].min()) if not hist_1y.empty else None

    avg_vol = float(volume.rolling(30).mean().iloc[-1])
    rel_volume = round(float(volume.iloc[-1]) / avg_vol, 2) if avg_vol else None

    sma_20 = _sma(close, 20)
    sma_50 = _sma(close, 50)
    sma_200 = _sma(close, 200)

    cross_signal = None
    if sma_50 and sma_200:
        cross_signal = "golden_cross" if sma_50 > sma_200 else "dead_cross"

    return {
        "ticker": ticker.upper(),
        "current_price": round(current_price, 4),
        "prev_close": round(prev_close, 4),
        "change_pct": round(change_pct, 2),
        "high_52w": round(high_52w, 4) if high_52w else None,
        "low_52w": round(low_52w, 4) if low_52w else None,
        "pct_from_52w_high": round((current_price - high_52w) / high_52w * 100, 2) if high_52w else None,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "cross_signal": cross_signal,
        "rsi_14": _rsi(close),
        "atr_14": _atr(hist),
        "volume_today": int(volume.iloc[-1]),
        "avg_volume_30d": int(avg_vol),
        "relative_volume": rel_volume,
        "data_period": period,
        "bars_count": len(hist),
    }
