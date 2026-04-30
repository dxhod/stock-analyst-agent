"""
Prompt builders for the multi-agent stock analyst workflow.
"""

import json


def _json(data: dict | list) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _language_rule(language: str) -> str:
    return (
        f"LANGUAGE LOCK: The output language is {language}. "
        "Use this language for every sentence, heading, table label, and bullet. "
        "Do not switch to English unless quoting a company name, ticker, metric name, or source title."
    )


def _summary_sections(language: str) -> str:
    normalized = language.lower()
    if "\u0440\u0443\u0441" in normalized:
        return """### 1. \u0413\u043b\u0430\u0432\u043d\u044b\u0439 \u0432\u044b\u0432\u043e\u0434
### 2. \u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u043a\u0430\u0440\u0442\u0438\u043d\u0430
### 3. \u0424\u0443\u043d\u0434\u0430\u043c\u0435\u043d\u0442\u0430\u043b\u044c\u043d\u044b\u0439 \u043e\u0431\u0437\u043e\u0440
### 4. \u041a\u0430\u0442\u0430\u043b\u0438\u0437\u0430\u0442\u043e\u0440\u044b \u0438 \u043d\u043e\u0432\u043e\u0441\u0442\u0438
### 5. \u0411\u044b\u0447\u0438\u0439 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439
### 6. \u041c\u0435\u0434\u0432\u0435\u0436\u0438\u0439 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439
### 7. \u041a\u0430\u0440\u0442\u0430 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0435\u0432
| \u0421\u0446\u0435\u043d\u0430\u0440\u0438\u0439 | \u0422\u0440\u0438\u0433\u0433\u0435\u0440 | \u0426\u0435\u043b\u0435\u0432\u0430\u044f \u0446\u0435\u043d\u0430 | \u0412\u0435\u0440\u043e\u044f\u0442\u043d\u043e\u0441\u0442\u044c |
|----------|---------|--------------|-------------|
| \u0411\u044b\u0447\u0438\u0439    |         |              |             |
| \u0411\u0430\u0437\u043e\u0432\u044b\u0439  |         |              |             |
| \u041c\u0435\u0434\u0432\u0435\u0436\u0438\u0439 |         |              |             |
### 8. \u0422\u043e\u0440\u0433\u043e\u0432\u044b\u0435 \u0438\u0434\u0435\u0438
### 9. \u0412\u0435\u0440\u0434\u0438\u043a\u0442"""

    if "\u0443\u043a\u0440\u0430" in normalized:
        return """### 1. \u0413\u043e\u043b\u043e\u0432\u043d\u0438\u0439 \u0432\u0438\u0441\u043d\u043e\u0432\u043e\u043a
### 2. \u0422\u0435\u0445\u043d\u0456\u0447\u043d\u0430 \u043a\u0430\u0440\u0442\u0438\u043d\u0430
### 3. \u0424\u0443\u043d\u0434\u0430\u043c\u0435\u043d\u0442\u0430\u043b\u044c\u043d\u0438\u0439 \u043e\u0433\u043b\u044f\u0434
### 4. \u041a\u0430\u0442\u0430\u043b\u0456\u0437\u0430\u0442\u043e\u0440\u0438 \u0442\u0430 \u043d\u043e\u0432\u0438\u043d\u0438
### 5. \u0411\u0438\u0447\u0430\u0447\u0438\u0439 \u0441\u0446\u0435\u043d\u0430\u0440\u0456\u0439
### 6. \u0412\u0435\u0434\u043c\u0435\u0436\u0438\u0439 \u0441\u0446\u0435\u043d\u0430\u0440\u0456\u0439
### 7. \u041a\u0430\u0440\u0442\u0430 \u0441\u0446\u0435\u043d\u0430\u0440\u0456\u0457\u0432
| \u0421\u0446\u0435\u043d\u0430\u0440\u0456\u0439 | \u0422\u0440\u0438\u0433\u0435\u0440 | \u0426\u0456\u043b\u044c\u043e\u0432\u0430 \u0446\u0456\u043d\u0430 | \u0419\u043c\u043e\u0432\u0456\u0440\u043d\u0456\u0441\u0442\u044c |
|----------|--------|--------------|-------------|
| \u0411\u0438\u0447\u0430\u0447\u0438\u0439  |        |              |             |
| \u0411\u0430\u0437\u043e\u0432\u0438\u0439  |        |              |             |
| \u0412\u0435\u0434\u043c\u0435\u0436\u0438\u0439 |        |              |             |
### 8. \u0422\u043e\u0440\u0433\u043e\u0432\u0456 \u0456\u0434\u0435\u0457
### 9. \u0412\u0435\u0440\u0434\u0438\u043a\u0442"""

    return """### 1. Edge Read
### 2. Technical Picture
### 3. Fundamental Snapshot
### 4. Catalyst and News Analysis
### 5. Bull Case
### 6. Bear Case
### 7. Scenario Map
| Scenario | Trigger | Price Target | Probability |
|----------|---------|--------------|-------------|
| Bull     |         |              |             |
| Base     |         |              |             |
| Bear     |         |              |             |
### 8. Trade Ideas
### 9. Verdict"""


def build_intent_prompt(
    user_query: str,
    cached_analysis: dict | None = None,
) -> str:
    cached_ticker = cached_analysis.get("ticker") if cached_analysis else None
    cached_tickers = cached_analysis.get("tickers") if cached_analysis else None
    return f"""You are an intent validator for a stock-analysis assistant.

User query:
{user_query}

Cached analysis ticker: {cached_ticker or "none"}
Cached analysis tickers: {cached_tickers or "none"}

Classify the request, extract all stock tickers, and detect the user's language.

Rules:
- If the user asks about a new company or ticker, set route to "new_analysis".
- If the user compares multiple companies or tickers, include every requested ticker in tickers.
- If the user asks a follow-up about the cached analysis, set route to "follow_up".
- If there is no cached analysis, never use "follow_up".
- Resolve well-known company names to US tickers when obvious, for example Tesla -> TSLA, Apple -> AAPL.
- The ticker field must contain the primary ticker symbol only, never the whole user query.
- The tickers field must be an array of uppercase ticker symbols. For comparison requests, include all compared tickers.
- For "Analyze Apple stock", return ticker "AAPL", not "ANALYZE APPLE STOCK".
- For "Compare NVDA and AAPL risks", return ticker "NVDA" and tickers ["NVDA", "AAPL"].
- Set language to the natural language used by the user, for example English, Russian, Ukrainian, Deutsch, Espanol, Francais.
- If the user mixes languages, choose the dominant language of the request.
- If there is no stock/company intent, set route to "unknown".
- Return exactly one valid JSON object. No markdown, no explanations, no text before or after JSON.

JSON schema:
{{
  "route": "new_analysis | follow_up | unknown",
  "ticker": "UPPERCASE_TICKER_OR_EMPTY",
  "tickers": ["UPPERCASE_TICKER"],
  "language": "DETECTED_LANGUAGE_NAME",
  "reason": "short reason"
}}
"""


def build_technical_prompt(price_data: dict, language: str) -> str:
    return f"""You are a technical-analysis agent.
{_language_rule(language)}

Use only this price dataset:
{_json(price_data)}

Return a concise technical view covering trend, support/resistance, RSI, volume, volatility, and actionable levels.
Be specific and avoid generic market commentary.
"""


def build_fundamental_prompt(fundamentals: dict, language: str) -> str:
    return f"""You are a fundamental-analysis agent.
{_language_rule(language)}

Use only this fundamentals dataset:
{_json(fundamentals)}

Return a concise fundamental view covering valuation, growth, profitability, balance sheet, cash flow, analyst targets, and key weaknesses.
Be specific and data-driven.
"""


def build_news_prompt(ticker: str, news_text: str, language: str) -> str:
    return f"""You are a market-news agent.
{_language_rule(language)}

Ticker: {ticker}
Recent news:
{news_text}

Return a concise catalyst view covering what matters, sentiment, upcoming risks/events, and how the news may affect price action.
Do not invent news that is not present.
"""


def build_summary_prompt(
    user_query: str,
    ticker: str,
    technical_analysis: str,
    fundamental_analysis: str,
    news_analysis: str,
    language: str,
) -> str:
    return f"""You are the lead portfolio analyst.
{_language_rule(language)}

User request:
{user_query}

Ticker:
{ticker}

Technical agent output:
{technical_analysis}

Fundamental agent output:
{fundamental_analysis}

News agent output:
{news_analysis}

Synthesize the three analyses into a direct answer to the user's request.
If the request contains multiple tickers, compare them directly and make clear which risks, strengths, and conclusions belong to each ticker.

Required sections:
{_summary_sections(language)}

Be specific, practical, and do not repeat the agents verbatim.
Do not offer to run a fresh analysis. This response is already the current analysis.
"""


def build_follow_up_prompt(
    user_query: str,
    cached_analysis: dict,
    conversation: list[dict[str, str]],
    language: str,
) -> str:
    return f"""You are a stock-analysis assistant continuing an existing conversation.
{_language_rule(language)}

User question:
{user_query}

Available context:
{_json(cached_analysis)}

Conversation:
{_json(conversation[-8:])}

Answer naturally and directly. Do not mention cached analysis, stored context, previous analysis, or internal agent outputs.
Do not offer to run a fresh analysis. Use the available workflow context to answer the question.
"""
