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
    if "рус" in normalized:
        return """### 1. Главный вывод
### 2. Техническая картина
### 3. Фундаментальный обзор
### 4. Катализаторы и новости
### 5. Бычий сценарий
### 6. Медвежий сценарий
### 7. Карта сценариев
| Сценарий | Триггер | Целевая цена | Вероятность |
|----------|---------|--------------|-------------|
| Бычий    |         |              |             |
| Базовый  |         |              |             |
| Медвежий |         |              |             |
### 8. Торговые идеи
### 9. Вердикт"""

    if "укра" in normalized:
        return """### 1. Головний висновок
### 2. Технічна картина
### 3. Фундаментальний огляд
### 4. Каталізатори та новини
### 5. Бичачий сценарій
### 6. Ведмежий сценарій
### 7. Карта сценаріїв
| Сценарій | Тригер | Цільова ціна | Ймовірність |
|----------|--------|--------------|-------------|
| Бичачий  |        |              |             |
| Базовий  |        |              |             |
| Ведмежий |        |              |             |
### 8. Торгові ідеї
### 9. Вердикт"""

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
    return f"""You are an intent validator for a stock-analysis assistant.

User query:
{user_query}

Cached analysis ticker: {cached_ticker or "none"}

Classify the request, extract the stock ticker, and detect the user's language.

Rules:
- If the user asks about a new company or ticker, set route to "new_analysis".
- If the user asks a follow-up about the cached analysis, set route to "follow_up".
- If there is no cached analysis, never use "follow_up".
- Resolve well-known company names to US tickers when obvious, for example Tesla -> TSLA, Apple -> AAPL.
- The ticker field must contain only the ticker symbol, never the whole user query.
- For "Analyze Apple stock", return ticker "AAPL", not "ANALYZE APPLE STOCK".
- Set language to the natural language used by the user, for example English, Русский, Українська, Deutsch, Español, Français.
- If the user mixes languages, choose the dominant language of the request.
- If there is no stock/company intent, set route to "unknown".
- Return only valid JSON. No markdown.

JSON schema:
{{
  "route": "new_analysis | follow_up | unknown",
  "ticker": "UPPERCASE_TICKER_OR_EMPTY",
  "language": "DETECTED_LANGUAGE_NAME",
  "reason": "short reason"
}}
"""


def build_technical_prompt(price_data: dict, language: str) -> str:
    return f"""You are a technical-analysis agent. Write the entire answer in {language}, including headings.
{_language_rule(language)}

Use only this price dataset:
{_json(price_data)}

Return a concise technical view covering trend, support/resistance, RSI, volume, volatility, and actionable levels.
Be specific and avoid generic market commentary.
"""


def build_fundamental_prompt(fundamentals: dict, language: str) -> str:
    return f"""You are a fundamental-analysis agent. Write the entire answer in {language}, including headings.
{_language_rule(language)}

Use only this fundamentals dataset:
{_json(fundamentals)}

Return a concise fundamental view covering valuation, growth, profitability, balance sheet, cash flow, analyst targets, and key weaknesses.
Be specific and data-driven.
"""


def build_news_prompt(ticker: str, news_text: str, language: str) -> str:
    return f"""You are a market-news agent. Write the entire answer in {language}, including headings.
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
    return f"""You are the lead portfolio analyst. Write the entire answer in {language}, including headings and table labels.
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

Required sections:
{_summary_sections(language)}

Be specific, practical, and do not repeat the agents verbatim.
"""


def build_follow_up_prompt(
    user_query: str,
    cached_analysis: dict,
    conversation: list[dict[str, str]],
    language: str,
) -> str:
    return f"""You are a stock-analysis assistant continuing an existing conversation. Write the entire answer in {language}.
{_language_rule(language)}

User question:
{user_query}

Available context:
{_json(cached_analysis)}

Conversation:
{_json(conversation[-8:])}

Answer naturally and directly. Do not mention cached analysis, stored context, previous analysis, or internal agent outputs.
If the user asks for fresh or real-time data, say that you can run a fresh analysis.
"""
