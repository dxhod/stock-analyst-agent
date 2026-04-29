import re

COMMON_COMPANY_TICKERS = {
    "apple": "AAPL",
    "tesla": "TSLA",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "amazon": "AMZN",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    "amd": "AMD",
    "intel": "INTC",
    "palantir": "PLTR",
    "berkshire": "BRK-B",
    "jpmorgan": "JPM",
    "visa": "V",
    "mastercard": "MA",
    "coca cola": "KO",
    "coca-cola": "KO",
    "walmart": "WMT",
    "disney": "DIS",
    "salesforce": "CRM",
    "oracle": "ORCL",
}

STOPWORDS = {
    "A",
    "AN",
    "THE",
    "STOCK",
    "STOCKS",
    "SHARE",
    "SHARES",
    "ANALYZE",
    "ANALYSE",
    "ANALYSIS",
    "PRICE",
    "COMPANY",
}

TICKER_RE = re.compile(r"^[A-Z]{1,5}([.-][A-Z])?$")


def normalize_ticker(user_query: str, raw_ticker: str | None) -> str:
    text = f"{user_query} {raw_ticker or ''}".lower()

    for company, ticker in COMMON_COMPANY_TICKERS.items():
        if company in text:
            return ticker

    candidate = (raw_ticker or "").upper().strip().replace("$", "")
    if TICKER_RE.match(candidate) and candidate not in STOPWORDS:
        return candidate

    query_tickers = re.findall(r"\$?([A-Z]{1,5}(?:[.-][A-Z])?)\b", user_query.upper())
    for ticker in query_tickers:
        if ticker not in STOPWORDS:
            return ticker

    return ""
