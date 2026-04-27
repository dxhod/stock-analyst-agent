"""
Tool: fundamental data
Fetches company profile, valuation multiples, margins, and analyst data.
No API key required — uses yfinance (Yahoo Finance).
"""

import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential


def _safe_float(value, digits: int = 4) -> float | None:
    """Safely cast yfinance values; return None on missing/NaN."""
    try:
        if value is None:
            return None
        f = float(value)
        if f != f:  # NaN check
            return None
        return round(f, digits)
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _fmt_large(value: int | None) -> str | None:
    """Format large numbers as human-readable strings (e.g. 2.3T, 400B, 5M)."""
    if value is None:
        return None
    abs_val = abs(value)
    if abs_val >= 1e12:
        return f"{value / 1e12:.2f}T"
    if abs_val >= 1e9:
        return f"{value / 1e9:.2f}B"
    if abs_val >= 1e6:
        return f"{value / 1e6:.2f}M"
    return str(value)


# ── Main fetch ─────────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def fetch_fundamentals(ticker: str) -> dict:
    """
    Return a structured dict with company fundamentals.

    Args:
        ticker: Stock symbol, e.g. "AAPL"

    Returns:
        dict with valuation, margins, growth, balance sheet, analyst data
    """
    tk = yf.Ticker(ticker.upper())
    info = tk.info

    if not info or "symbol" not in info:
        raise ValueError(f"No fundamental data found for '{ticker}'.")

    market_cap_raw = _safe_int(info.get("marketCap"))
    revenue_raw = _safe_int(info.get("totalRevenue"))
    fcf_raw = _safe_int(info.get("freeCashflow"))

    return {
        "ticker": ticker.upper(),
        # Profile
        "company_name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "employees": _safe_int(info.get("fullTimeEmployees")),
        # Size
        "market_cap": market_cap_raw,
        "market_cap_fmt": _fmt_large(market_cap_raw),
        "enterprise_value": _safe_int(info.get("enterpriseValue")),
        # Valuation
        "pe_trailing": _safe_float(info.get("trailingPE"), 2),
        "pe_forward": _safe_float(info.get("forwardPE"), 2),
        "peg_ratio": _safe_float(info.get("pegRatio"), 2),
        "price_to_book": _safe_float(info.get("priceToBook"), 2),
        "price_to_sales": _safe_float(info.get("priceToSalesTrailing12Months"), 2),
        "ev_to_ebitda": _safe_float(info.get("enterpriseToEbitda"), 2),
        "ev_to_revenue": _safe_float(info.get("enterpriseToRevenue"), 2),
        # Income
        "revenue_ttm": revenue_raw,
        "revenue_ttm_fmt": _fmt_large(revenue_raw),
        "revenue_growth_yoy": _safe_float(info.get("revenueGrowth")),
        "earnings_growth_yoy": _safe_float(info.get("earningsGrowth")),
        "gross_margin": _safe_float(info.get("grossMargins")),
        "operating_margin": _safe_float(info.get("operatingMargins")),
        "net_margin": _safe_float(info.get("profitMargins")),
        "ebitda": _safe_int(info.get("ebitda")),
        # Returns
        "return_on_assets": _safe_float(info.get("returnOnAssets")),
        "return_on_equity": _safe_float(info.get("returnOnEquity")),
        # Cash & debt
        "free_cash_flow": fcf_raw,
        "free_cash_flow_fmt": _fmt_large(fcf_raw),
        "total_cash": _safe_int(info.get("totalCash")),
        "total_debt": _safe_int(info.get("totalDebt")),
        "debt_to_equity": _safe_float(info.get("debtToEquity"), 2),
        "current_ratio": _safe_float(info.get("currentRatio"), 2),
        # Dividends & shares
        "dividend_yield": _safe_float(info.get("dividendYield")),
        "payout_ratio": _safe_float(info.get("payoutRatio")),
        "shares_outstanding": _safe_int(info.get("sharesOutstanding")),
        "float_shares": _safe_int(info.get("floatShares")),
        "short_float_pct": _safe_float(info.get("shortPercentOfFloat")),
        # Risk
        "beta": _safe_float(info.get("beta"), 2),
        # Analyst consensus
        "analyst_target_mean": _safe_float(info.get("targetMeanPrice"), 2),
        "analyst_target_low": _safe_float(info.get("targetLowPrice"), 2),
        "analyst_target_high": _safe_float(info.get("targetHighPrice"), 2),
        "analyst_recommendation": info.get("recommendationKey"),
        "analyst_count": _safe_int(info.get("numberOfAnalystOpinions")),
        # Description (trimmed for prompt budget)
        "description": (info.get("longBusinessSummary") or "")[:600],
    }
