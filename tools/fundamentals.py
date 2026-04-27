"""
Tool: fundamental data via Financial Modeling Prep API
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


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def fetch_fundamentals(ticker: str) -> dict:
    profile = _get(f"profile/{ticker.upper()}")
    ratios = _get(f"ratios-ttm/{ticker.upper()}")
    metrics = _get(f"key-metrics-ttm/{ticker.upper()}")

    p = profile[0] if profile else {}
    r = ratios[0] if ratios else {}
    m = metrics[0] if metrics else {}

    market_cap = _safe(p.get("mktCap"), 0)
    revenue = _safe(m.get("revenuePerShareTTM"), 0)
    fcf = _safe(m.get("freeCashFlowPerShareTTM"), 0)

    return {
        "ticker": ticker.upper(),
        "company_name": p.get("companyName"),
        "sector": p.get("sector"),
        "industry": p.get("industry"),
        "country": p.get("country"),
        "employees": p.get("fullTimeEmployees"),
        "market_cap": market_cap,
        "market_cap_fmt": _fmt_large(market_cap),
        "enterprise_value": _safe(m.get("enterpriseValueTTM"), 0),
        "pe_trailing": _safe(r.get("peRatioTTM"), 2),
        "pe_forward": _safe(p.get("pe"), 2),
        "peg_ratio": _safe(r.get("pegRatioTTM"), 2),
        "price_to_book": _safe(r.get("priceToBookRatioTTM"), 2),
        "price_to_sales": _safe(r.get("priceToSalesRatioTTM"), 2),
        "ev_to_ebitda": _safe(m.get("evToEbitdaTTM"), 2),
        "ev_to_revenue": _safe(m.get("evToFreeCashFlowTTM"), 2),
        "revenue_ttm": revenue,
        "revenue_ttm_fmt": _fmt_large(revenue),
        "revenue_growth_yoy": _safe(r.get("revenueGrowthTTM")),
        "earnings_growth_yoy": _safe(r.get("epsgrowthTTM")),
        "gross_margin": _safe(r.get("grossProfitMarginTTM")),
        "operating_margin": _safe(r.get("operatingProfitMarginTTM")),
        "net_margin": _safe(r.get("netProfitMarginTTM")),
        "return_on_assets": _safe(r.get("returnOnAssetsTTM")),
        "return_on_equity": _safe(r.get("returnOnEquityTTM")),
        "free_cash_flow": fcf,
        "free_cash_flow_fmt": _fmt_large(fcf),
        "total_cash": None,
        "total_debt": _safe(m.get("netDebtTTM"), 0),
        "debt_to_equity": _safe(r.get("debtEquityRatioTTM"), 2),
        "current_ratio": _safe(r.get("currentRatioTTM"), 2),
        "dividend_yield": _safe(r.get("dividendYieldTTM")),
        "payout_ratio": _safe(r.get("payoutRatioTTM")),
        "shares_outstanding": None,
        "float_shares": None,
        "short_float_pct": None,
        "beta": _safe(p.get("beta"), 2),
        "analyst_target_mean": _safe(p.get("dcf"), 2),
        "analyst_target_low": None,
        "analyst_target_high": None,
        "analyst_recommendation": p.get("recommendationKey"),
        "analyst_count": None,
        "description": (p.get("description") or "")[:600],
    }
