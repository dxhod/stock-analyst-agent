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
    "COMPARE",
    "COMPARING",
    "RISK",
    "RISKS",
    "VERSUS",
    "VS",
    "AND",
    "OR",
}

TICKER_RE = re.compile(r"^[A-Z]{1,5}([.-][A-Z])?$")
QUERY_TICKER_RE = re.compile(r"(?<![A-Z])\$?([A-Z]{1,5}(?:[.-][A-Z])?)\b")
RAW_TICKER_RE = re.compile(r"\$?([A-Z]{1,5}(?:[.-][A-Z])?)")


def _append_unique(tickers: list[str], ticker: str) -> None:
    ticker = ticker.upper().strip().replace("$", "")
    if ticker and TICKER_RE.match(ticker) and ticker not in STOPWORDS and ticker not in tickers:
        tickers.append(ticker)


def _iter_raw_tickers(value: str | list[str] | None) -> list[str]:
    if not value:
        return []

    values = [value] if isinstance(value, str) else value
    tickers: list[str] = []
    for item in values:
        for match in RAW_TICKER_RE.finditer(str(item).upper()):
            _append_unique(tickers, match.group(1))
    return tickers


def normalize_tickers(
    user_query: str,
    raw_ticker: str | None = None,
    raw_tickers: list[str] | str | None = None,
) -> list[str]:
    model_tickers = _iter_raw_tickers(raw_tickers) + _iter_raw_tickers(raw_ticker)
    text = f"{user_query} {' '.join(model_tickers)}".lower()
    tickers: list[str] = []
    candidates: list[tuple[int, str]] = []

    for company, ticker in COMMON_COMPANY_TICKERS.items():
        for match in re.finditer(rf"\b{re.escape(company)}\b", text):
            candidates.append((match.start(), ticker))

    known_company_words = {
        word.upper()
        for company in COMMON_COMPANY_TICKERS
        for word in re.findall(r"[A-Za-z]+", company)
    }
    for match in QUERY_TICKER_RE.finditer(user_query.upper()):
        ticker = match.group(1)
        if ticker not in known_company_words:
            candidates.append((match.start(), ticker))

    for _, ticker in sorted(candidates, key=lambda item: item[0]):
        _append_unique(tickers, ticker)

    for ticker in model_tickers:
        _append_unique(tickers, ticker)

    return tickers


def normalize_ticker(user_query: str, raw_ticker: str | None) -> str:
    tickers = normalize_tickers(user_query, raw_ticker)
    if tickers:
        return tickers[0]

    return ""
