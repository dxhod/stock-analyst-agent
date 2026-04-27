"""
Tool: price & OHLCV data
Fetches historical prices and computes core technical indicators.
No API key required — uses yfinance (Yahoo Finance).
"""

import yfinance as yf
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential


# ── Indicator helpers ──────────────────────────────────────────────────────────

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
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)


def _atr(hist: pd.DataFrame, period: int = 14) -> float | None:
    """Average True Range — proxy for volatility."""
    if len(hist) < period + 1:
        return None
    high, low, close = hist["High"], hist["Low"], hist["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return round(float(tr.rolling(period).mean().iloc[-1]), 4)


# ── Main fetch ─────────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def fetch_price_data(ticker: str, period: str = "6mo") -> dict:
    """
    Return a structured dict with price data and technical indicators.

    Args:
        ticker: Stock symbol, e.g. "AAPL"
        period: yfinance period string — "1mo", "3mo", "6mo", "1y", "2y"

    Returns:
        dict with keys: ticker, price metrics, SMA/RSI/ATR, volume stats
    """
    tk = yf.Ticker(ticker.upper())
    hist = tk.history(period=period)

    if hist.empty:
        raise ValueError(f"No price data found for '{ticker}'. Check the ticker symbol.")

    close = hist["Close"]
    volume = hist["Volume"]

    current_price = float(close.iloc[-1])
    prev_close = float(close.iloc[-2])
    change_pct = (current_price - prev_close) / prev_close * 100

    # 52-week range requires at least 1y of data
    hist_1y = tk.history(period="1y")
    high_52w = float(hist_1y["High"].max()) if not hist_1y.empty else None
    low_52w = float(hist_1y["Low"].min()) if not hist_1y.empty else None

    # Volume relative to 30-day avg (>1.5 = elevated)
    avg_vol_30 = float(volume.rolling(30).mean().iloc[-1])
    rel_volume = round(float(volume.iloc[-1]) / avg_vol_30, 2) if avg_vol_30 else None

    sma_20 = _sma(close, 20)
    sma_50 = _sma(close, 50)
    sma_200 = _sma(close, 200)

    # Golden / dead cross signal
    cross_signal = None
    if sma_50 and sma_200:
        cross_signal = "golden_cross" if sma_50 > sma_200 else "dead_cross"

    return {
        "ticker": ticker.upper(),
        # Price
        "current_price": round(current_price, 4),
        "prev_close": round(prev_close, 4),
        "change_pct": round(change_pct, 2),
        # Range
        "high_52w": round(high_52w, 4) if high_52w else None,
        "low_52w": round(low_52w, 4) if low_52w else None,
        "pct_from_52w_high": round((current_price - high_52w) / high_52w * 100, 2) if high_52w else None,
        # Moving averages
        "sma_20": sma_20,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "cross_signal": cross_signal,
        # Momentum
        "rsi_14": _rsi(close),
        # Volatility
        "atr_14": _atr(hist),
        # Volume
        "volume_today": int(volume.iloc[-1]),
        "avg_volume_30d": int(avg_vol_30),
        "relative_volume": rel_volume,
        # Meta
        "data_period": period,
        "bars_count": len(hist),
    }
