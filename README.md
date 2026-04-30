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
- 30-minute conversation and analysis cache.
- Streaming final response in the Streamlit chat UI.
- Automatic language detection from the user query.
- Local JSONL agent run logging for prompt/output inspection.
- Configurable Groq model routing with summarizer fallback models.

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
```

Fallback behavior is currently used for the summarizer. If the primary summary model hits a rate limit, the workflow retries the fallback chain.

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
| Market data | yfinance |
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
| `GROQ_MODEL` | No | Default model for specialist and follow-up agents |
| `GROQ_INTENT_MODEL` | No | Model used by the intent validator |
| `GROQ_SUMMARY_MODEL` | No | Primary model used by the summarizer |
| `GROQ_SUMMARY_FALLBACK_MODELS` | No | Comma-separated fallback models for the summarizer |
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
|-- tools/
|   |-- price_data.py          # OHLCV and technical indicators
|   |-- fundamentals.py        # Fundamental metrics
|   |-- news_fetcher.py        # Recent news
|
|-- examples/
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

---

## License

MIT
