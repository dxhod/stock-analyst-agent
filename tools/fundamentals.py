"""
Tool: fundamental data via yfinance
"""

import yfinance as yf
from curl_cffi import requests as curl_requests
from tenacity import retry, stop_after_attempt, wait_exponential

yf.set_tz_cache_location("/tmp")
session = curl_requests.Session(impersonate="chrome")


def _safe(value, digits: int = 4) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
        return None if f != f else round(f, digits)
    except (TypeError, ValueError):
        return None


def _fmt_large(value) -> str | None:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    abs_v = abs(v)
    if abs_v >= 1e12:
        return f"{v/1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{v/1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{v/1e6:.2f}M"
    return str(int(v))


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=2, max=10))
def fetch_fundamentals(ticker: str) -> dict:
    tk = yf.Ticker(ticker.upper(), session=session)
    info = tk.info

    if not info or "symbol" not in info:
        raise ValueError(f"No fundamental data for '{ticker}'")

    market_cap = _safe(info.get("marketCap"), 0)
    revenue = _safe(info.get("totalRevenue"), 0)
    fcf = _safe(info.get("freeCashflow"), 0)

    return {
        "ticker": ticker.upper(),
        "company_name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "employees": info.get("fullTimeEmployees"),
        "market_cap": market_cap,
        "market_cap_fmt": _fmt_large(market_cap),
        "enterprise_value": _safe(info.get("enterpriseValue"), 0),
        "pe_trailing": _safe(info.get("trailingPE"), 2),
        "pe_forward": _safe(info.get("forwardPE"), 2),
        "peg_ratio": _safe(info.get("pegRatio"), 2),
        "price_to_book": _safe(info.get("priceToBook"), 2),
        "price_to_sales": _safe(info.get("priceToSalesTrailing12Months"), 2),
        "ev_to_ebitda": _safe(info.get("enterpriseToEbitda"), 2),
        "ev_to_revenue": _safe(info.get("enterpriseToRevenue"), 2),
        "revenue_ttm": revenue,
        "revenue_ttm_fmt": _fmt_large(revenue),
        "revenue_growth_yoy": _safe(info.get("revenueGrowth")),
        "earnings_growth_yoy": _safe(info.get("earningsGrowth")),
        "gross_margin": _safe(info.get("grossMargins")),
        "operating_margin": _safe(info.get("operatingMargins")),
        "net_margin": _safe(info.get("profitMargins")),
        "return_on_assets": _safe(info.get("returnOnAssets")),
        "return_on_equity": _safe(info.get("returnOnEquity")),
        "free_cash_flow": fcf,
        "free_cash_flow_fmt": _fmt_large(fcf),
        "total_cash": _safe(info.get("totalCash"), 0),
        "total_debt": _safe(info.get("totalDebt"), 0),
        "debt_to_equity": _safe(info.get("debtToEquity"), 2),
        "current_ratio": _safe(info.get("currentRatio"), 2),
        "dividend_yield": _safe(info.get("dividendYield")),
        "payout_ratio": _safe(info.get("payoutRatio")),
        "shares_outstanding": _safe(info.get("sharesOutstanding"), 0),
        "float_shares": _safe(info.get("floatShares"), 0),
        "short_float_pct": _safe(info.get("shortPercentOfFloat")),
        "beta": _safe(info.get("beta"), 2),
        "analyst_target_mean": _safe(info.get("targetMeanPrice"), 2),
        "analyst_target_low": _safe(info.get("targetLowPrice"), 2),
        "analyst_target_high": _safe(info.get("targetHighPrice"), 2),
        "analyst_recommendation": info.get("recommendationKey"),
        "analyst_count": info.get("numberOfAnalystOpinions"),
        "description": (info.get("longBusinessSummary") or "")[:600],
    }
