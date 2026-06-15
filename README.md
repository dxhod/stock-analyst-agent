# Stock Analyst Agent

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-6B4FBB?logo=langchain&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLM_Routing-F55036?logo=groq&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Chat_UI-FF4B4B?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22C55E)

Multi-agent equity research app built with LangGraph, Groq, yfinance, and Streamlit.

The user can ask for a ticker, company, comparison, or follow-up question. The system validates intent, resolves one or more stock tickers, fetches market datasets, runs specialist agents in parallel, and streams a final portfolio-style answer into the conversation.

Live demo: [stock-analyst-agent-production.up.railway.app](https://stock-analyst-agent-production.up.railway.app)

---

## Features

- Natural-language stock queries: ask for a ticker, company name, or full question.
- Multi-ticker comparisons: for example, `Compare NVDA and Apple risks`.
- Intent validation: detects whether the request is a new analysis, follow-up, or unknown request.
- Automatic ticker resolution: maps well-known company names such as Apple, Tesla, Microsoft, Nvidia, Amazon, and others to US tickers.
- Parallel specialist agents:
  - Technical agent
  - Fundamental agent
  - News agent
- Summarizer agent: combines specialist outputs into one structured answer.
- Follow-up agent: answers follow-up questions using the cached analysis context.
- Portfolio Builder: builds a stock/ETF portfolio from a guided Streamlit UI quiz or full form, using S&P 500/Nasdaq 100 candidates with a local fallback universe.
- 30-minute conversation and analysis cache.
- Streaming final response in the Streamlit chat UI.
- Automatic language detection from the user query.
- Local JSONL agent run logging for prompt/output inspection.
- Configurable Groq model routing with summarizer fallback models.
- Localized Portfolio Builder UI in English, German, Ukrainian, Russian, and Spanish.
- Optional RAG knowledge base with Qdrant Cloud and Gemini Embedding.
- Product knowledge agent that answers project/setup/architecture questions from RAG docs.
- Educational disclaimer for generated portfolio allocations.

---

## Architecture

```text
User query
    |
    v
Intent Validator
    |
    |-- unknown ---------------------------> Error / guidance
    |
    |-- follow_up + valid cache -----------> Follow-up Agent
    |
    |-- new_analysis ----------------------> Ticker Resolver
                                                |
                                                v
                                      Data Fetching Layer
                                      - price data
                                      - fundamentals
                                      - recent news
                                                |
                                                v
                             Parallel Specialist Agent Fanout
                             - Technical Agent
                             - Fundamental Agent
                             - News Agent
                                                |
                                                v
                                      Summarizer Agent
                                                |
                                                v
                                      Streamed chat response
```

The workflow is implemented as a LangGraph `StateGraph` in `agents/orchestrator.py`.

The primary state object is `AgentState`, which carries the user query, detected language, resolved ticker list, fetched datasets, specialist analyses, final answer, cached analysis, and error state.

---

## Multi-Ticker Workflow

The app supports both single-stock and comparison requests.

Examples:

```text
Analyze Tesla stock
Compare NVDA and AAPL risks
Compare Microsoft and Apple risks
What is the bull case for Amazon?
```

For a comparison query like:

```text
Compare NVDA and Apple risks
```

the intent layer resolves:

```json
{
  "ticker": "NVDA",
  "tickers": ["NVDA", "AAPL"]
}
```

Then the data layer fetches datasets for both symbols:

```text
price_data_by_ticker:
  NVDA -> price dataset
  AAPL -> price dataset

fundamentals_by_ticker:
  NVDA -> fundamentals dataset
  AAPL -> fundamentals dataset

news_by_ticker:
  NVDA -> recent news
  AAPL -> recent news
```

The technical, fundamental, and news agents receive multi-ticker datasets and the summarizer produces a comparative answer.

---

## Agents

### Intent Validator

Classifies the request as:

- `new_analysis`
- `follow_up`
- `product_knowledge`
- `unknown`

It also detects the output language and extracts all requested tickers. A deterministic ticker resolver is used as a guardrail so obvious tickers and company names are not missed if the LLM returns incomplete JSON.

### Technical Agent

Uses price data and technical indicators from yfinance. It focuses on:

- trend
- support and resistance
- RSI
- volume
- volatility
- actionable levels

### Fundamental Agent

Uses company fundamentals from yfinance. It focuses on:

- valuation
- growth
- profitability
- balance sheet
- cash flow
- analyst targets
- weaknesses

### News Agent

Uses recent headlines from yfinance. It focuses on:

- catalysts
- sentiment
- upcoming events
- risks that may affect price action

### Summarizer Agent

Combines the three specialist outputs into a structured investment answer. For comparison requests, it directly compares the requested tickers and separates risks, strengths, and conclusions by company.

### Follow-Up Agent

Uses the cached analysis and recent conversation context to answer follow-up questions without rerunning the full workflow unless the user asks about a new ticker or company.

### Product Knowledge Agent

Answers questions about the project itself using RAG context from product documentation. It is intended for questions about architecture, setup, Portfolio Builder implementation, RAG configuration, Railway variables, deployment, and integration details.

### Portfolio Builder

Builds a markdown portfolio proposal from the Streamlit Portfolio Builder UI, not from normal chat messages. Users can either walk through a one-question-at-a-time guided quiz or open the full form. The first quiz step selects the UI/output language: English, German, Ukrainian, Russian, or Spanish.

The builder asks for investment amount, number of holdings, risk level, horizon, style, ETF preference, sector tilts, sectors to avoid, and cash buffer. It loads S&P 500 and Nasdaq 100 constituents from external sources when available, adds a small ETF universe, falls back to a local large-cap list if needed, scores candidates deterministically, and constructs weights locally.

The LLM does not choose tickers or weights. It can optionally polish the final portfolio explanation when `GROQ_PORTFOLIO_USE_LLM_SUMMARY=true`; otherwise the app returns a local markdown summary. If Groq hits a token/rate limit, the portfolio flow falls back to local markdown instead of failing. The response is informational only and not financial advice.

### Market Data Fallback

Yahoo Finance via `yfinance` is the default market data provider for prices, fundamentals, and news. Because Yahoo endpoints are unofficial and can be unreliable from cloud hosts, the app can fall back to Finnhub when Yahoo does not return usable data.

Set `FINNHUB_API_KEY` to enable fallback. Keep `MARKET_DATA_PROVIDER=yahoo` for normal operation: Yahoo is tried first, then Finnhub is used only after a Yahoo failure. Set `MARKET_DATA_PROVIDER=finnhub` only when you want to bypass Yahoo and test Finnhub directly.

Finnhub free-tier keys may not include historical candles, price targets, or recommendation endpoints. For that reason, the default fallback mode is conservative:

```env
MARKET_DATA_PROVIDER=yahoo
FINNHUB_USE_CANDLES=false
FINNHUB_USE_ANALYST_ENDPOINTS=false
```

With candles disabled, Finnhub price fallback uses quote and 52-week metric data, so technical fields such as SMA, RSI, ATR, and volume may be unavailable. Portfolio Builder also skips ETF fundamentals and scores candidates in parallel to keep fallback mode responsive.

### RAG Knowledge Base

The app can optionally retrieve product, methodology, sector, disclaimer, and company notes from a Qdrant Cloud vector collection. Embeddings are generated with Google Gemini Embedding (`gemini-embedding-001`). RAG context is used only as background for explanations; it does not change Portfolio Builder scoring, tickers, weights, or allocations.

Local documents live in:

```text
rag/docs/
|-- product_overview.md
|-- portfolio_methodology.md
|-- style_explanations.md
|-- sector_notes.md
|-- disclaimer.md
|-- companies/
```

Ingest them into Qdrant:

```bash
python -m rag.ingest
```

Use `--dry-run` to count chunks without writing:

```bash
python -m rag.ingest --dry-run
```

---

## Cache and Follow-Up Questions

The app keeps the current conversation and analysis context for 30 minutes.

This allows flows like:

```text
User: Compare NVDA and Apple risks
Assistant: [full comparative analysis]

User: Which one looks safer right now?
Assistant: [follow-up answer using the cached comparison]
```

If a follow-up contains a new ticker or company not present in the cached analysis, the workflow switches to a new analysis automatically.

---

## Model Routing

The app uses Groq-hosted models through configurable environment variables.

Recommended free-tier-friendly setup:

```env
GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_INTENT_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_SUMMARY_MODEL=openai/gpt-oss-120b
GROQ_SUMMARY_FALLBACK_MODELS=llama-3.3-70b-versatile,meta-llama/llama-4-scout-17b-16e-instruct
GROQ_PORTFOLIO_USE_LLM_SUMMARY=false
GROQ_PORTFOLIO_SUMMARY_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_PORTFOLIO_SUMMARY_FALLBACK_MODELS=llama-3.3-70b-versatile,openai/gpt-oss-120b
RAG_ENABLED=false
RAG_TOP_K=4
QDRANT_URL=https://your-qdrant-cluster-url
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=stock_analyst_knowledge
GEMINI_API_KEY=your-gemini-api-key
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_EMBEDDING_DIMENSIONS=768
```

Fallback behavior is currently used for the summarizer. If the primary summary model hits a rate limit, the workflow retries the fallback chain.

Portfolio Builder has separate summary routing because portfolio prompts can otherwise consume Groq token-per-minute limits quickly. The default recommended setting is `GROQ_PORTFOLIO_USE_LLM_SUMMARY=false` for stable local markdown output. Set it to `true` when you want LLM-polished explanations.

RAG is disabled by default. Set `RAG_ENABLED=true` after creating a Qdrant Cloud collection and ingesting local docs.

---

## Local Agent Logs

Every LLM agent call can be logged locally to:

```text
logs/agent_runs.jsonl
```

Each JSONL record includes:

- timestamp
- run id
- agent name
- model
- primary ticker
- ticker list
- detected language
- user query
- prompt input
- model output

The `logs/` folder is ignored by git.

---

## Stack

| Layer | Technology |
|-------|------------|
| Agent workflow | LangGraph |
| LLM provider | Groq |
| Market data | yfinance with Finnhub fallback |
| UI | Streamlit |
| Environment config | python-dotenv |
| Logging | Local JSONL |
| Deployment | Railway |

---

## Quick Start

```bash
git clone https://github.com/dxhod/stock-analyst-agent.git
cd stock-analyst-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

Add your Groq API key to `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
```

On macOS/Linux, use:

```bash
source .venv/bin/activate
cp .env.example .env
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key |
| `MARKET_DATA_PROVIDER` | No | Set to `finnhub` to bypass Yahoo/yfinance and use Finnhub directly. Defaults to Yahoo with Finnhub fallback |
| `FINNHUB_API_KEY` | No | Finnhub API key used as a fallback when Yahoo/yfinance does not return usable market data |
| `FINNHUB_USE_CANDLES` | No | Set to `true` only when your Finnhub plan supports historical candle data. Defaults to quote-only fallback |
| `FINNHUB_USE_ANALYST_ENDPOINTS` | No | Set to `true` only when your Finnhub plan supports price target and recommendation endpoints. Defaults to disabled |
| `GROQ_MODEL` | No | Default model for specialist and follow-up agents |
| `GROQ_INTENT_MODEL` | No | Model used by the intent validator |
| `GROQ_SUMMARY_MODEL` | No | Primary model used by the summarizer |
| `GROQ_SUMMARY_FALLBACK_MODELS` | No | Comma-separated fallback models for the summarizer |
| `GROQ_PORTFOLIO_USE_LLM_SUMMARY` | No | Enable LLM-polished Portfolio Builder summaries. Defaults to local markdown when false |
| `GROQ_PORTFOLIO_SUMMARY_MODEL` | No | Primary model for optional Portfolio Builder summaries |
| `GROQ_PORTFOLIO_SUMMARY_FALLBACK_MODELS` | No | Comma-separated fallback models for optional Portfolio Builder summaries |
| `RAG_ENABLED` | No | Enable retrieval from the Qdrant knowledge base |
| `RAG_TOP_K` | No | Number of RAG snippets to retrieve. Default: `4` |
| `QDRANT_URL` | No | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | No | Qdrant Cloud API key |
| `QDRANT_COLLECTION` | No | Qdrant collection name. Default: `stock_analyst_knowledge` |
| `GEMINI_API_KEY` | No | Google Gemini API key for embeddings |
| `GEMINI_EMBEDDING_MODEL` | No | Gemini embedding model. Default: `gemini-embedding-001` |
| `GEMINI_EMBEDDING_DIMENSIONS` | No | Embedding dimensions. Default: `768` |
| `AGENT_LOG_DIR` | No | Directory for local JSONL logs. Default: `logs` |
| `LANGFUSE_PUBLIC_KEY` | No | Optional observability key |
| `LANGFUSE_SECRET_KEY` | No | Optional observability key |
| `LANGFUSE_HOST` | No | Optional LangFuse host |

---

## Project Structure

```text
stock-analyst-agent/
|-- app.py                     # Streamlit chat UI
|-- requirements.txt
|-- .env.example
|-- README.md
|
|-- agents/
|   |-- orchestrator.py        # LangGraph nodes, edges, model routing
|   |-- state.py               # AgentState TypedDict
|   |-- cache.py               # 30-minute analysis cache helpers
|   |-- ticker_resolver.py     # Company name and ticker normalization
|   |-- language_detector.py   # Deterministic language guardrail
|   |-- run_logger.py          # Local JSONL logging
|
|-- prompts/
|   |-- analysis.py            # Prompt builders for all agents
|
|-- rag/
|   |-- docs/                  # Local methodology/company knowledge docs
|   |-- embeddings.py          # Gemini Embedding REST client
|   |-- ingest.py              # Ingest docs into Qdrant
|   |-- qdrant_store.py        # Qdrant REST client
|   |-- retriever.py           # RAG retrieval helper
|
|-- tools/
|   |-- price_data.py          # OHLCV and technical indicators
|   |-- fundamentals.py        # Fundamental metrics
|   |-- news_fetcher.py        # Recent news
|   |-- portfolio_builder.py   # Stock/ETF universe, scoring, and allocation builder
|
|-- examples/
|-- test_portfolio_builder.py
|-- logs/                      # Local logs, ignored by git
```

---

## Example Questions

```text
Analyze Tesla stock
Compare NVDA and Apple risks
What is the bull case for Microsoft?
Which stock looks safer right now?
What could invalidate the bullish thesis?
```

Portfolio construction is available in the Streamlit **Portfolio Builder** section. Use **Start guided portfolio quiz** for a step-by-step localized flow, or **Open full portfolio form** for a compact form.

---

## License

MIT
