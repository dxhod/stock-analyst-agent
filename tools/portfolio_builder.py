from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import pandas as pd

from tools.fundamentals import fetch_fundamentals
from tools.price_data import fetch_price_data


SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"

DEFAULT_ETFS = [
    {"ticker": "VTI", "name": "Vanguard Total Stock Market ETF", "sector": "Broad Market", "type": "ETF"},
    {"ticker": "VOO", "name": "Vanguard S&P 500 ETF", "sector": "Broad Market", "type": "ETF"},
    {"ticker": "QQQ", "name": "Invesco QQQ Trust", "sector": "Growth / Nasdaq 100", "type": "ETF"},
    {"ticker": "SCHD", "name": "Schwab U.S. Dividend Equity ETF", "sector": "Dividend", "type": "ETF"},
    {"ticker": "VIG", "name": "Vanguard Dividend Appreciation ETF", "sector": "Dividend", "type": "ETF"},
    {"ticker": "XLK", "name": "Technology Select Sector SPDR Fund", "sector": "Technology", "type": "ETF"},
    {"ticker": "XLV", "name": "Health Care Select Sector SPDR Fund", "sector": "Healthcare", "type": "ETF"},
    {"ticker": "XLF", "name": "Financial Select Sector SPDR Fund", "sector": "Financial Services", "type": "ETF"},
]

FALLBACK_STOCKS = [
    ("AAPL", "Apple Inc.", "Technology"),
    ("MSFT", "Microsoft Corporation", "Technology"),
    ("NVDA", "NVIDIA Corporation", "Technology"),
    ("AMZN", "Amazon.com, Inc.", "Consumer Cyclical"),
    ("META", "Meta Platforms, Inc.", "Communication Services"),
    ("GOOGL", "Alphabet Inc.", "Communication Services"),
    ("AVGO", "Broadcom Inc.", "Technology"),
    ("TSLA", "Tesla, Inc.", "Consumer Cyclical"),
    ("LLY", "Eli Lilly and Company", "Healthcare"),
    ("JPM", "JPMorgan Chase & Co.", "Financial Services"),
    ("V", "Visa Inc.", "Financial Services"),
    ("MA", "Mastercard Incorporated", "Financial Services"),
    ("UNH", "UnitedHealth Group Incorporated", "Healthcare"),
    ("COST", "Costco Wholesale Corporation", "Consumer Defensive"),
    ("HD", "The Home Depot, Inc.", "Consumer Cyclical"),
    ("PG", "The Procter & Gamble Company", "Consumer Defensive"),
    ("KO", "The Coca-Cola Company", "Consumer Defensive"),
    ("PEP", "PepsiCo, Inc.", "Consumer Defensive"),
    ("MRK", "Merck & Co., Inc.", "Healthcare"),
    ("ABBV", "AbbVie Inc.", "Healthcare"),
    ("XOM", "Exxon Mobil Corporation", "Energy"),
    ("CVX", "Chevron Corporation", "Energy"),
    ("LIN", "Linde plc", "Basic Materials"),
    ("CAT", "Caterpillar Inc.", "Industrials"),
    ("GE", "GE Aerospace", "Industrials"),
    ("ADBE", "Adobe Inc.", "Technology"),
    ("CRM", "Salesforce, Inc.", "Technology"),
    ("AMD", "Advanced Micro Devices, Inc.", "Technology"),
    ("NFLX", "Netflix, Inc.", "Communication Services"),
    ("MCD", "McDonald's Corporation", "Consumer Cyclical"),
]


@dataclass(frozen=True)
class Candidate:
    ticker: str
    name: str
    sector: str
    type: str


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper().replace(".", "-")


def load_equity_universe() -> list[Candidate]:
    candidates: dict[str, Candidate] = {}

    try:
        sp500 = pd.read_html(SP500_URL)[0]
        for _, row in sp500.iterrows():
            ticker = _normalize_ticker(str(row.get("Symbol", "")))
            if ticker:
                candidates[ticker] = Candidate(
                    ticker=ticker,
                    name=str(row.get("Security", ticker)),
                    sector=str(row.get("GICS Sector", "Unknown")),
                    type="Stock",
                )
    except Exception:
        pass

    try:
        tables = pd.read_html(NASDAQ100_URL)
        nasdaq = next((table for table in tables if "Ticker" in table.columns), None)
        if nasdaq is not None:
            for _, row in nasdaq.iterrows():
                ticker = _normalize_ticker(str(row.get("Ticker", "")))
                if ticker and ticker not in candidates:
                    candidates[ticker] = Candidate(
                        ticker=ticker,
                        name=str(row.get("Company", ticker)),
                        sector=str(row.get("GICS Sector", "Unknown")),
                        type="Stock",
                    )
    except Exception:
        pass

    if not candidates:
        for ticker, name, sector in FALLBACK_STOCKS:
            candidates[ticker] = Candidate(ticker=ticker, name=name, sector=sector, type="Stock")

    for item in DEFAULT_ETFS:
        candidates[item["ticker"]] = Candidate(**item)

    return list(candidates.values())


def normalize_preferences(preferences: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(preferences or {})
    normalized.setdefault("currency", "USD")
    normalized["investment_amount"] = float(normalized.get("investment_amount") or 10000)
    normalized["holdings_count"] = int(normalized.get("holdings_count") or 10)
    normalized["holdings_count"] = max(3, min(normalized["holdings_count"], 25))
    normalized["risk"] = normalized.get("risk") or "Balanced"
    normalized["horizon"] = normalized.get("horizon") or "1-3yr"
    normalized["style"] = normalized.get("style") or "Balanced"
    normalized["etf_preference"] = normalized.get("etf_preference") or "Mixed"
    normalized["cash_pct"] = float(normalized.get("cash_pct") if normalized.get("cash_pct") is not None else 0)
    normalized["cash_pct"] = max(0, min(normalized["cash_pct"], 20))
    normalized["overweight_sectors"] = normalized.get("overweight_sectors") or []
    normalized["avoid_sectors"] = normalized.get("avoid_sectors") or []
    return normalized


def missing_required_preferences(preferences: dict[str, Any]) -> list[str]:
    required = [
        "investment_amount",
        "holdings_count",
        "risk",
        "horizon",
        "style",
        "etf_preference",
        "cash_pct",
    ]
    return [field for field in required if preferences.get(field) in (None, "", [])]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        value = float(value)
        return default if value != value else value
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _score_lower_better(value: Any, good: float, bad: float) -> float:
    value = _safe_float(value, bad)
    if bad == good:
        return 50
    return _clamp((bad - value) / (bad - good) * 100)


def _score_higher_better(value: Any, bad: float, good: float) -> float:
    value = _safe_float(value, bad)
    if good == bad:
        return 50
    return _clamp((value - bad) / (good - bad) * 100)


def _sector_match(sector: str, themes: list[str]) -> bool:
    sector_l = sector.lower()
    return any(str(theme).lower() in sector_l or sector_l in str(theme).lower() for theme in themes)


def _select_candidates(universe: list[Candidate], preferences: dict[str, Any]) -> list[Candidate]:
    style = preferences["style"]
    etf_preference = preferences["etf_preference"]
    overweight = preferences["overweight_sectors"]
    avoid = preferences["avoid_sectors"]

    etfs = [candidate for candidate in universe if candidate.type == "ETF"]
    stocks = [candidate for candidate in universe if candidate.type == "Stock"]

    preferred = [
        candidate
        for candidate in stocks
        if _sector_match(candidate.sector, overweight) and not _sector_match(candidate.sector, avoid)
    ]
    neutral = [
        candidate
        for candidate in stocks
        if candidate not in preferred and not _sector_match(candidate.sector, avoid)
    ]

    style_bias = {
        "Growth": ["Technology", "Communication Services", "Consumer Cyclical"],
        "Dividend": ["Consumer Defensive", "Healthcare", "Energy", "Financial"],
        "Defensive": ["Consumer Defensive", "Healthcare", "Utilities"],
        "Quality": ["Technology", "Healthcare", "Consumer Defensive", "Financial"],
        "Value": ["Financial", "Energy", "Industrials", "Healthcare"],
    }.get(style, [])
    styled = [candidate for candidate in neutral if _sector_match(candidate.sector, style_bias)]
    others = [candidate for candidate in neutral if candidate not in styled]

    max_stocks = 36 if etf_preference != "ETF-heavy" else 24
    pool = preferred[:12] + styled[:18] + others[:max_stocks]
    if etf_preference != "Stocks-only":
        pool = etfs + pool

    seen = set()
    unique: list[Candidate] = []
    for candidate in pool:
        if candidate.ticker not in seen:
            seen.add(candidate.ticker)
            unique.append(candidate)
    return unique[:60]


def _score_candidate(candidate: Candidate, preferences: dict[str, Any]) -> dict[str, Any] | None:
    try:
        price = fetch_price_data(candidate.ticker)
        fundamentals = {} if candidate.type == "ETF" else fetch_fundamentals(candidate.ticker)
    except Exception:
        return None

    if candidate.type == "ETF":
        base = 68
        if preferences["etf_preference"] == "ETF-heavy":
            base += 16
        elif preferences["etf_preference"] == "Mixed":
            base += 8
        if preferences["risk"] == "Conservative":
            base += 8
        if preferences["style"] in {"Dividend", "Defensive"} and candidate.ticker in {"SCHD", "VIG", "XLV"}:
            base += 8
        if preferences["style"] == "Growth" and candidate.ticker in {"QQQ", "XLK"}:
            base += 8
        return {
            "ticker": candidate.ticker,
            "name": candidate.name,
            "sector": candidate.sector,
            "type": candidate.type,
            "score": round(_clamp(base), 2),
            "role": "Core diversified exposure",
            "price_data": price,
            "fundamentals": fundamentals,
        }

    quality = (
        _score_higher_better(fundamentals.get("net_margin"), -0.1, 0.35)
        + _score_higher_better(fundamentals.get("return_on_equity"), 0.0, 0.35)
        + _score_higher_better(fundamentals.get("free_cash_flow"), 0, 20_000_000_000)
        + _score_lower_better(fundamentals.get("debt_to_equity"), 250, 20)
    ) / 4
    growth = (
        _score_higher_better(fundamentals.get("revenue_growth_yoy"), -0.05, 0.25)
        + _score_higher_better(fundamentals.get("earnings_growth_yoy"), -0.1, 0.3)
        + _score_higher_better(fundamentals.get("analyst_target_mean") or price.get("current_price"), price.get("current_price"), price.get("current_price") * 1.35)
    ) / 3
    valuation = (
        _score_lower_better(fundamentals.get("pe_forward"), 12, 45)
        + _score_lower_better(fundamentals.get("price_to_sales"), 2, 15)
        + _score_lower_better(fundamentals.get("ev_to_ebitda"), 8, 35)
    ) / 3
    momentum = (
        _score_higher_better(price.get("current_price"), price.get("sma_200") or price.get("current_price") * 1.2, price.get("sma_50") or price.get("current_price"))
        + _score_higher_better(price.get("relative_volume"), 0.6, 1.8)
        + (100 - abs((_safe_float(price.get("rsi_14"), 50) - 55) * 2))
    ) / 3
    risk = (
        _score_lower_better(fundamentals.get("beta"), 0.8, 2.0)
        + _score_higher_better(price.get("pct_from_52w_high"), -45, -5)
        + _score_higher_better(fundamentals.get("current_ratio"), 0.7, 2.0)
    ) / 3
    income = (
        _score_higher_better(fundamentals.get("dividend_yield"), 0, 0.04)
        + _score_lower_better(fundamentals.get("payout_ratio"), 0.85, 0.2)
    ) / 2

    weights = {
        "Growth": {"quality": 0.22, "growth": 0.30, "valuation": 0.12, "momentum": 0.22, "risk": 0.10, "income": 0.04},
        "Value": {"quality": 0.24, "growth": 0.12, "valuation": 0.30, "momentum": 0.10, "risk": 0.16, "income": 0.08},
        "Dividend": {"quality": 0.24, "growth": 0.08, "valuation": 0.14, "momentum": 0.08, "risk": 0.18, "income": 0.28},
        "Quality": {"quality": 0.34, "growth": 0.18, "valuation": 0.14, "momentum": 0.10, "risk": 0.18, "income": 0.06},
        "Defensive": {"quality": 0.30, "growth": 0.08, "valuation": 0.16, "momentum": 0.06, "risk": 0.30, "income": 0.10},
    }.get(preferences["style"], {"quality": 0.24, "growth": 0.18, "valuation": 0.18, "momentum": 0.16, "risk": 0.16, "income": 0.08})

    if preferences["risk"] == "Aggressive":
        weights["growth"] += 0.04
        weights["momentum"] += 0.04
        weights["risk"] -= 0.04
        weights["valuation"] -= 0.04
    elif preferences["risk"] == "Conservative":
        weights["quality"] += 0.04
        weights["risk"] += 0.06
        weights["momentum"] -= 0.04
        weights["growth"] -= 0.06

    score = (
        quality * weights["quality"]
        + growth * weights["growth"]
        + valuation * weights["valuation"]
        + momentum * weights["momentum"]
        + risk * weights["risk"]
        + income * weights["income"]
    )
    if _sector_match(candidate.sector, preferences["overweight_sectors"]):
        score *= 1.12
    if _sector_match(candidate.sector, preferences["avoid_sectors"]):
        score *= 0.6

    return {
        "ticker": candidate.ticker,
        "name": fundamentals.get("company_name") or candidate.name,
        "sector": fundamentals.get("sector") or candidate.sector,
        "type": candidate.type,
        "score": round(_clamp(score), 2),
        "role": _role_for(candidate, preferences),
        "subscores": {
            "quality": round(quality, 1),
            "growth": round(growth, 1),
            "valuation": round(valuation, 1),
            "momentum": round(momentum, 1),
            "risk": round(risk, 1),
            "income": round(income, 1),
        },
        "price_data": price,
        "fundamentals": fundamentals,
    }


def _role_for(candidate: Candidate, preferences: dict[str, Any]) -> str:
    if preferences["style"] == "Dividend":
        return "Income and stability sleeve"
    if preferences["style"] == "Growth":
        return "Growth satellite"
    if preferences["style"] == "Defensive":
        return "Defensive equity exposure"
    if preferences["style"] == "Value":
        return "Value-oriented equity exposure"
    return "Quality equity compounder"


def _target_etf_count(count: int, preferences: dict[str, Any]) -> int:
    if preferences["etf_preference"] == "Stocks-only":
        return 0
    if preferences["etf_preference"] == "ETF-heavy":
        return max(1, min(count - 1, round(count * 0.45)))
    return max(1, round(count * 0.25))


def _construct_allocations(scored: list[dict[str, Any]], preferences: dict[str, Any]) -> list[dict[str, Any]]:
    count = preferences["holdings_count"]
    cash_slots = 1 if preferences["cash_pct"] > 0 else 0
    asset_count = max(2, count - cash_slots)
    etf_count = _target_etf_count(asset_count, preferences)

    etfs = [item for item in scored if item["type"] == "ETF"][:etf_count]
    stocks = [item for item in scored if item["type"] == "Stock"]
    selected = etfs + stocks[: max(0, asset_count - len(etfs))]

    investable_pct = 100 - preferences["cash_pct"]
    base_cap = {"Conservative": 16, "Balanced": 20, "Aggressive": 25}.get(preferences["risk"], 20)
    max_weight = max(base_cap, investable_pct / max(asset_count, 1) * 1.35)
    min_weight = 3
    raw_total = sum(max(item["score"], 1) for item in selected) or 1

    allocations = []
    for item in selected:
        weight = investable_pct * max(item["score"], 1) / raw_total
        weight = max(min_weight, min(max_weight, weight))
        allocations.append({**item, "weight_pct": weight})

    scale = investable_pct / (sum(item["weight_pct"] for item in allocations) or 1)
    for item in allocations:
        item["weight_pct"] = round(item["weight_pct"] * scale, 2)
        item["allocation_amount"] = round(preferences["investment_amount"] * item["weight_pct"] / 100, 2)

    if preferences["cash_pct"] > 0:
        allocations.append(
            {
                "ticker": "CASH",
                "name": f"{preferences['currency']} cash buffer",
                "sector": "Cash",
                "type": "Cash",
                "score": None,
                "role": "Dry powder and volatility buffer",
                "weight_pct": round(preferences["cash_pct"], 2),
                "allocation_amount": round(preferences["investment_amount"] * preferences["cash_pct"] / 100, 2),
            }
        )

    drift = round(100 - sum(item["weight_pct"] for item in allocations), 2)
    if allocations and abs(drift) >= 0.01:
        allocations[0]["weight_pct"] = round(allocations[0]["weight_pct"] + drift, 2)
        allocations[0]["allocation_amount"] = round(preferences["investment_amount"] * allocations[0]["weight_pct"] / 100, 2)

    return allocations


def _compact_allocation(item: dict[str, Any]) -> dict[str, Any]:
    compact = {
        "ticker": item.get("ticker"),
        "name": item.get("name"),
        "sector": item.get("sector"),
        "type": item.get("type"),
        "score": item.get("score"),
        "role": item.get("role"),
        "weight_pct": item.get("weight_pct"),
        "allocation_amount": item.get("allocation_amount"),
    }
    if item.get("subscores"):
        compact["subscores"] = item["subscores"]
    return compact


def build_portfolio(preferences: dict[str, Any]) -> dict[str, Any]:
    preferences = normalize_preferences(preferences)
    universe = load_equity_universe()
    candidates = _select_candidates(universe, preferences)

    scored = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_score_candidate, candidate, preferences) for candidate in candidates]
        for future in as_completed(futures):
            result = future.result()
            if result:
                scored.append(result)

    scored.sort(key=lambda item: item["score"] or 0, reverse=True)
    if not scored:
        raise ValueError("No portfolio candidates could be scored from the available data sources.")
    allocations = _construct_allocations(scored, preferences)

    return {
        "preferences": preferences,
        "universe_size": len(universe),
        "scored_candidates": len(scored),
        "allocations": [_compact_allocation(item) for item in allocations],
        "total_weight_pct": round(sum(item["weight_pct"] for item in allocations), 2),
        "rebalance": "Review monthly; rebalance when a position drifts more than 20% from target weight or the thesis changes.",
        "disclaimer": "Informational only; not financial advice.",
    }
