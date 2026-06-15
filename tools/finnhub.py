"""
Fallback market data provider via Finnhub.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from time import time
from typing import Any

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


BASE_URL = "https://finnhub.io/api/v1"
TIMEOUT = 12


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _api_key() -> str:
    return os.getenv("FINNHUB_API_KEY", "").strip()


def _require_api_key() -> str:
    api_key = _api_key()
    if not api_key:
        raise ValueError("FINNHUB_API_KEY is missing for Finnhub fallback.")
    return api_key


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def _get(path: str, **params: Any) -> dict | list:
    params["token"] = _require_api_key()
    response = requests.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise ValueError(str(payload["error"]))
    return payload


def _safe(value: Any, digits: int = 4) -> float | None:
    try:
        if value is None or value == "":
            return None
        f = float(value)
        return None if f != f else round(f, digits)
    except (TypeError, ValueError):
        return None


def _ratio(value: Any, digits: int = 4) -> float | None:
    number = _safe(value, digits + 2)
    if number is None:
        return None
    if abs(number) > 1.5:
        number /= 100
    return round(number, digits)


def _fmt_large(value: Any) -> str | None:
    number = _safe(value, 0)
    if number is None:
        return None
    abs_v = abs(number)
    if abs_v >= 1e12:
        return f"{number / 1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{number / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{number / 1e6:.2f}M"
    return str(int(number))


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


def _candles_to_frame(payload: dict) -> pd.DataFrame:
    if payload.get("s") != "ok":
        raise ValueError(f"Finnhub did not return candle data: {payload.get('s')}")
    rows = {
        "Open": payload.get("o", []),
        "High": payload.get("h", []),
        "Low": payload.get("l", []),
        "Close": payload.get("c", []),
        "Volume": payload.get("v", []),
    }
    hist = pd.DataFrame(rows)
    if hist.empty:
        raise ValueError("Finnhub returned empty candle data.")
    return hist


def fetch_price_data(ticker: str, period: str = "6mo") -> dict:
    symbol = ticker.upper()
    now = int(time())
    from_ts = now - (370 * 24 * 60 * 60)
    quote = _get("/quote", symbol=symbol)
    hist_1y = pd.DataFrame()
    if _env_bool("FINNHUB_USE_CANDLES", False):
        try:
            candles = _get("/stock/candle", symbol=symbol, resolution="D", **{"from": from_ts, "to": now})
            hist_1y = _candles_to_frame(candles)
        except Exception:
            hist_1y = pd.DataFrame()

    current_price = _safe(quote.get("c"))
    prev_close = _safe(quote.get("pc"))
    if current_price is None or prev_close is None:
        raise ValueError("Finnhub quote did not return current and previous close prices.")

    if hist_1y.empty:
        metrics_payload = _get("/stock/metric", symbol=symbol, metric="all")
        metrics = metrics_payload.get("metric", {}) if isinstance(metrics_payload, dict) else {}
        high_52w = _safe(metrics.get("52WeekHigh"))
        low_52w = _safe(metrics.get("52WeekLow"))
        return {
            "ticker": symbol,
            "current_price": round(current_price, 4),
            "prev_close": round(prev_close, 4),
            "change_pct": round((current_price - prev_close) / prev_close * 100, 2) if prev_close else 0,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "pct_from_52w_high": round((current_price - high_52w) / high_52w * 100, 2) if high_52w else None,
            "sma_20": None,
            "sma_50": None,
            "sma_200": None,
            "cross_signal": None,
            "rsi_14": None,
            "atr_14": None,
            "volume_today": None,
            "avg_volume_30d": None,
            "relative_volume": None,
            "data_period": period,
            "bars_count": 0,
            "data_provider": "finnhub",
        }

    hist = hist_1y.tail(126 if period == "6mo" else len(hist_1y))
    close = hist["Close"]
    volume = hist["Volume"]
    change_pct = (current_price - prev_close) / prev_close * 100 if prev_close else 0
    high_52w = float(hist_1y["High"].max()) if not hist_1y.empty else None
    low_52w = float(hist_1y["Low"].min()) if not hist_1y.empty else None
    avg_vol = float(volume.rolling(30).mean().iloc[-1])
    rel_volume = round(float(volume.iloc[-1]) / avg_vol, 2) if avg_vol else None
    sma_50 = _sma(close, 50)
    sma_200 = _sma(close, 200)

    return {
        "ticker": symbol,
        "current_price": round(current_price, 4),
        "prev_close": round(prev_close, 4),
        "change_pct": round(change_pct, 2),
        "high_52w": round(high_52w, 4) if high_52w else None,
        "low_52w": round(low_52w, 4) if low_52w else None,
        "pct_from_52w_high": round((current_price - high_52w) / high_52w * 100, 2) if high_52w else None,
        "sma_20": _sma(close, 20),
        "sma_50": sma_50,
        "sma_200": sma_200,
        "cross_signal": "golden_cross" if sma_50 and sma_200 and sma_50 > sma_200 else "dead_cross" if sma_50 and sma_200 else None,
        "rsi_14": _rsi(close),
        "atr_14": _atr(hist),
        "volume_today": int(volume.iloc[-1]),
        "avg_volume_30d": int(avg_vol),
        "relative_volume": rel_volume,
        "data_period": period,
        "bars_count": len(hist),
        "data_provider": "finnhub",
    }


def fetch_fundamentals(ticker: str) -> dict:
    symbol = ticker.upper()
    profile = _get("/stock/profile2", symbol=symbol)
    metrics_payload = _get("/stock/metric", symbol=symbol, metric="all")
    target = {}
    recommendations = []
    if _env_bool("FINNHUB_USE_ANALYST_ENDPOINTS", False):
        try:
            target = _get("/stock/price-target", symbol=symbol)
        except Exception:
            target = {}
        try:
            recommendations = _get("/stock/recommendation", symbol=symbol)
        except Exception:
            recommendations = []

    metrics = metrics_payload.get("metric", {}) if isinstance(metrics_payload, dict) else {}
    latest_recommendation = recommendations[0] if isinstance(recommendations, list) and recommendations else {}
    recommendation_key = None
    if latest_recommendation:
        scores = {
            "strong_buy": latest_recommendation.get("strongBuy", 0),
            "buy": latest_recommendation.get("buy", 0),
            "hold": latest_recommendation.get("hold", 0),
            "sell": latest_recommendation.get("sell", 0),
            "strong_sell": latest_recommendation.get("strongSell", 0),
        }
        recommendation_key = max(scores, key=scores.get)

    market_cap = _safe(profile.get("marketCapitalization"), 0)
    if market_cap is not None:
        market_cap *= 1_000_000

    return {
        "ticker": symbol,
        "company_name": profile.get("name"),
        "sector": profile.get("finnhubIndustry"),
        "industry": profile.get("finnhubIndustry"),
        "country": profile.get("country"),
        "employees": None,
        "market_cap": market_cap,
        "market_cap_fmt": _fmt_large(market_cap),
        "enterprise_value": None,
        "pe_trailing": _safe(metrics.get("peTTM"), 2),
        "pe_forward": _safe(metrics.get("forwardPE"), 2),
        "peg_ratio": _safe(metrics.get("pegTTM"), 2),
        "price_to_book": _safe(metrics.get("pbAnnual") or metrics.get("pbQuarterly"), 2),
        "price_to_sales": _safe(metrics.get("psTTM"), 2),
        "ev_to_ebitda": _safe(metrics.get("evToEbitdaTTM"), 2),
        "ev_to_revenue": _safe(metrics.get("evToRevenueTTM"), 2),
        "revenue_ttm": None,
        "revenue_ttm_fmt": None,
        "revenue_growth_yoy": _ratio(metrics.get("revenueGrowthTTMYoy")),
        "earnings_growth_yoy": _ratio(metrics.get("epsGrowthTTMYoy")),
        "gross_margin": _ratio(metrics.get("grossMarginTTM")),
        "operating_margin": _ratio(metrics.get("operatingMarginTTM")),
        "net_margin": _ratio(metrics.get("netProfitMarginTTM")),
        "return_on_assets": _ratio(metrics.get("roaTTM")),
        "return_on_equity": _ratio(metrics.get("roeTTM")),
        "free_cash_flow": None,
        "free_cash_flow_fmt": None,
        "total_cash": None,
        "total_debt": None,
        "debt_to_equity": _safe(metrics.get("totalDebt/totalEquityAnnual") or metrics.get("totalDebt/totalEquityQuarterly"), 2),
        "current_ratio": _safe(metrics.get("currentRatioAnnual") or metrics.get("currentRatioQuarterly"), 2),
        "dividend_yield": _ratio(metrics.get("dividendYieldIndicatedAnnual")),
        "payout_ratio": _ratio(metrics.get("payoutRatioAnnual")),
        "shares_outstanding": _safe(profile.get("shareOutstanding"), 0),
        "float_shares": None,
        "short_float_pct": None,
        "beta": _safe(metrics.get("beta"), 2),
        "analyst_target_mean": _safe(target.get("targetMean"), 2) if isinstance(target, dict) else None,
        "analyst_target_low": _safe(target.get("targetLow"), 2) if isinstance(target, dict) else None,
        "analyst_target_high": _safe(target.get("targetHigh"), 2) if isinstance(target, dict) else None,
        "analyst_recommendation": recommendation_key,
        "analyst_count": sum(latest_recommendation.get(key, 0) for key in ("strongBuy", "buy", "hold", "sell", "strongSell")) or None,
        "description": "",
        "data_provider": "finnhub",
    }


def fetch_news(ticker: str, max_items: int = 10) -> list[dict]:
    symbol = ticker.upper()
    to_date = date.today()
    from_date = to_date - timedelta(days=14)
    payload = _get(
        "/company-news",
        symbol=symbol,
        **{"from": from_date.isoformat(), "to": to_date.isoformat()},
    )
    if not isinstance(payload, list):
        raise ValueError("Finnhub returned invalid news payload.")

    results = []
    for item in payload[:max_items]:
        headline = (item.get("headline") or "").strip()
        if not headline:
            continue
        published = item.get("datetime")
        date_str = date.fromtimestamp(published).isoformat() if published else ""
        results.append({
            "title": headline,
            "date": date_str,
            "days_ago": (date.today() - date.fromtimestamp(published)).days if published else None,
            "source": item.get("source") or "unknown",
            "summary": (item.get("summary") or "")[:400],
            "url": item.get("url") or "",
        })
    return results
