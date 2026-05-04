# Stock Analyst Agent Product Overview

Stock Analyst Agent is a Streamlit and LangGraph application for equity analysis, follow-up questions, and stock/ETF portfolio construction.

## Product Purpose

The product helps users analyze public equities and build educational stock/ETF portfolio proposals. It is designed as an analyst assistant, not as an execution platform or financial advisor.

Core goals:

- Answer natural-language stock analysis questions.
- Compare multiple tickers in one request.
- Support follow-up questions using cached context.
- Build stock/ETF portfolios through a structured Portfolio Builder UI.
- Use deterministic portfolio scoring and allocation logic.
- Optionally enrich explanations with RAG knowledge base context.
- Keep all outputs informational and not financial advice.

## Main User Workflows

### Stock Analysis

Users can ask questions such as:

- Analyze Tesla stock
- Compare NVDA and Apple risks
- What is the bull case for Microsoft?
- Which stock looks safer right now?

The app validates intent, resolves tickers, fetches market data, runs specialist agents, and streams a final structured answer.

### Follow-Up Questions

The app stores recent analysis context for 30 minutes. If the user asks a follow-up question about the previous analysis, the follow-up agent answers using cached context instead of rerunning the full workflow.

### Portfolio Builder

Portfolio Builder is launched from the Streamlit UI, not from normal chat messages. It has two modes:

- Guided quiz: one question at a time.
- Full form: all portfolio inputs at once.

The first Portfolio Builder step selects the UI/output language:

- English
- Deutsch
- Українська
- Русский
- Español

Portfolio inputs:

- Investment amount
- Number of holdings
- Risk level
- Investment horizon
- Portfolio style
- ETF preference
- Cash buffer
- Sectors/themes to overweight
- Sectors/themes to avoid

The frontend sends a structured `PORTFOLIO_BUILDER_REQUEST` payload to the backend. The user sees a human-readable request in the chat history, not raw JSON.

## Architecture

High-level components:

- `app.py`: Streamlit UI, chat composer, Portfolio Builder UI, localized labels, streaming display.
- `agents/orchestrator.py`: LangGraph workflow, routing, data fetching, specialist agents, summarizers, Portfolio Builder node, RAG integration.
- `agents/state.py`: shared LangGraph state.
- `agents/ticker_resolver.py`: deterministic ticker/name normalization guardrail.
- `agents/cache.py`: 30-minute cached analysis context.
- `prompts/analysis.py`: prompt builders for intent, specialist agents, summaries, portfolio summaries, and product knowledge responses.
- `tools/price_data.py`: yfinance price and technical data.
- `tools/fundamentals.py`: yfinance company fundamentals.
- `tools/news_fetcher.py`: yfinance recent news.
- `tools/portfolio_builder.py`: deterministic stock/ETF universe, scoring, and allocation builder.
- `rag/`: Qdrant/Gemini RAG modules, ingestion scripts, and local knowledge base documents.

## LangGraph Routes

The main workflow routes:

- `new_analysis`: ticker/company analysis.
- `follow_up`: question about cached analysis.
- `portfolio_builder`: internal UI payload only.
- `product_knowledge`: questions about this product/project/application.
- `unknown`: unsupported requests.

Portfolio Builder is intentionally not triggered by normal chat text such as "build me a portfolio". It is launched through the UI to keep the experience structured and localized.

## Specialist Agents

### Technical Agent

Uses price data and technical indicators. It covers trend, support/resistance, RSI, volume, volatility, and actionable levels.

### Fundamental Agent

Uses yfinance fundamentals. It covers valuation, growth, profitability, balance sheet, cash flow, analyst targets, and weaknesses.

### News Agent

Uses recent yfinance headlines. It covers catalysts, sentiment, events, and news-driven risks.

### Summarizer Agent

Combines technical, fundamental, news, and optional RAG context into a final answer. RAG context is background only and must not override live data or agent outputs.

### Product Knowledge Agent

Answers questions about the project itself using RAG context from product documentation. It should explain architecture, setup, Portfolio Builder logic, RAG configuration, environment variables, deployment notes, and integration details. If retrieved context is missing, it should say that product knowledge context is unavailable.

## Portfolio Builder Logic

The Portfolio Builder is deterministic. LLMs do not choose tickers, scores, weights, cash allocation, or dollar allocations.

Universe:

- S&P 500 constituents from Wikipedia when available.
- Nasdaq 100 constituents from Wikipedia when available.
- ETF universe: VTI, VOO, QQQ, SCHD, VIG, XLK, XLV, XLF.
- Local fallback large-cap stock universe.

Scoring buckets:

- Quality
- Growth
- Valuation
- Momentum
- Risk
- Income

User style changes bucket weights:

- Growth emphasizes growth and momentum.
- Value emphasizes valuation.
- Dividend emphasizes income and stability.
- Quality emphasizes profitability and balance-sheet strength.
- Defensive emphasizes risk and quality.
- Balanced spreads weights across buckets.

Risk changes concentration and bucket tilts:

- Conservative lowers concentration and emphasizes quality/risk.
- Balanced uses default caps.
- Aggressive allows higher concentration and more growth/momentum exposure.

ETF preference controls ETF share:

- Stocks-only: no ETF sleeve.
- Mixed: roughly 25% of positions can be ETFs.
- ETF-heavy: roughly 45% of positions can be ETFs.

Cash buffer reserves 0-20% of the portfolio.

## RAG Integration

RAG is optional and disabled by default. It uses:

- Qdrant Cloud for vector storage.
- Google Gemini Embedding (`gemini-embedding-001`) for embeddings.

RAG documents live in `rag/docs/`.

Document groups:

- Product documentation
- Portfolio methodology
- Style explanations
- Sector notes
- Disclaimer notes
- Company knowledge base notes

Ingestion command:

```bash
python -m rag.ingest
```

Dry run command:

```bash
python -m rag.ingest --dry-run
```

RAG is used as background context for:

- Stock analysis summary.
- Portfolio Builder explanations.
- Product knowledge questions.

RAG must not change calculated portfolio weights, tickers, scores, or live market data.

## Environment Variables

Core:

- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GROQ_INTENT_MODEL`
- `GROQ_SUMMARY_MODEL`
- `GROQ_SUMMARY_FALLBACK_MODELS`

Portfolio summary:

- `GROQ_PORTFOLIO_USE_LLM_SUMMARY`
- `GROQ_PORTFOLIO_SUMMARY_MODEL`
- `GROQ_PORTFOLIO_SUMMARY_FALLBACK_MODELS`

RAG:

- `RAG_ENABLED`
- `RAG_TOP_K`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `QDRANT_COLLECTION`
- `GEMINI_API_KEY`
- `GEMINI_EMBEDDING_MODEL`
- `GEMINI_EMBEDDING_DIMENSIONS`

Logging:

- `AGENT_LOG_DIR`

Observability:

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST`

## Deployment Notes

The application is deployed on Railway. Railway variables should include Groq credentials and, if RAG is enabled, Qdrant and Gemini credentials.

RAG ingestion does not need to run on every deploy. Documents are ingested into Qdrant separately, and the Railway app only needs read/search access through environment variables.

## Safety and Compliance

The product output is informational and educational only. It is not personalized financial, investment, tax, legal, or accounting advice.

The app should avoid claiming certainty about future returns. Portfolio Builder outputs should include a disclaimer and should present allocation proposals as model-based educational examples.

## Known Limitations

- yfinance data can be delayed, incomplete, or temporarily unavailable.
- Groq free/on-demand token limits can affect LLM summaries.
- RAG quality depends on the quality and freshness of ingested documents.
- Portfolio Builder scoring is a simplified model and cannot predict future performance.
- Localized UI labels are handled in `app.py`; deeper i18n infrastructure may be needed as the product grows.
