# 📈 Stock Analyst Agent

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-6B4FBB?logo=langchain&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?logo=groq&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-FF4B4B?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22C55E)

An agentic stock analysis pipeline built with **LangGraph** that autonomously fetches market data, runs fundamental and technical analysis, and produces a structured 9-section investment report — all at zero API cost.

> **Live demo →** [stock-analyst-agent-production.up.railway.app](https://stock-analyst-agent-production.up.railway.app)

---

## How it works

```
Ticker input
     │
     ▼
LangGraph Orchestrator  ──────────────────────────────────────┐
     │                                                         │
     ├──▶  yfinance (prices · OHLCV · technicals)             │
     ├──▶  yfinance (fundamentals · ratios · analyst data)    │ tools/
     └──▶  news fetcher (headlines · dates · sources)         │
                                                              ─┘
     │  aggregated data
     ▼
Groq LLM — Llama 3.3 70B
     │  9-section structured analysis
     ▼
Streamlit UI  ──▶  Markdown / PDF report
```

The graph has two nodes: `fetch_data` (parallel tool calls) and `run_analysis` (LLM synthesis). A conditional edge skips analysis if data fetching fails, keeping the agent resilient.

---

## Report sections

| # | Section | What it covers |
|---|---------|----------------|
| 1 | **Edge Read** | Single most important analytical insight right now |
| 2 | **Technical Picture** | HTF/ITF/LTF structure, key levels, RSI, volume |
| 3 | **Fundamental Snapshot** | Valuation vs. sector, earnings quality, FCF |
| 4 | **Catalyst & News Analysis** | Price drivers, upcoming events, macro context |
| 5 | **Bull Case** | 3 specific, quantified upside arguments |
| 6 | **Bear Case** | 3 specific, quantified risks |
| 7 | **Scenario Map** | Bull / Base / Bear with price targets and probabilities |
| 8 | **Trade Ideas** | Entry, stop, target, R:R, timeframe, invalidation |
| 9 | **Verdict** | One-sentence bias with conviction level |

---

## Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent framework | LangGraph | State machine with typed state, conditional edges, easy to extend |
| LLM | Groq / Llama 3.3 70B | Free tier, ~300 tok/s, great for structured output |
| Market data | yfinance | No API key, covers prices + fundamentals + news |
| UI | Streamlit | Fast to build, easy to deploy, looks good for portfolio |
| Observability | LangFuse | Traces, costs, latency — optional but recommended |
| Reliability | tenacity | Retry logic on all data fetches |

---

## Quick start

### Option 1 — GitHub Codespaces (recommended)

Click **Code → Codespaces → Create codespace** on this repo. Everything runs in the browser.

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your GROQ_API_KEY to .env (free at console.groq.com)
streamlit run app.py
```

### Option 2 — Local

```bash
git clone https://github.com/dxhod/stock-analyst-agent.git
cd stock-analyst-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add GROQ_API_KEY to .env
streamlit run app.py
```

---

## Project structure

```
stock-analyst-agent/
├── app.py                     # Streamlit UI
├── requirements.txt
├── .env.example
│
├── agents/
│   ├── orchestrator.py        # LangGraph StateGraph — nodes, edges, graph compile
│   └── state.py               # AgentState TypedDict
│
├── tools/
│   ├── price_data.py          # OHLCV + SMA/RSI/ATR/volume via yfinance
│   ├── fundamentals.py        # 30+ fundamental metrics via yfinance
│   └── news_fetcher.py        # Recent headlines with dates and sources
│
├── formatters/                # MD and PDF export (coming soon)
├── evals/                     # Output quality tests (coming soon)
└── examples/
    └── AAPL_report.md         # Sample report output
```

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Free at [console.groq.com](https://console.groq.com) |
| `LANGFUSE_PUBLIC_KEY` | ⬜ | Observability — [langfuse.com](https://langfuse.com) |
| `LANGFUSE_SECRET_KEY` | ⬜ | Observability |
| `LANGFUSE_HOST` | ⬜ | Default: `https://cloud.langfuse.com` |

---

## Extending the agent

The LangGraph graph is easy to extend with new nodes:

```python
# Add a new node
graph.add_node("fetch_sec_filings", fetch_sec_node)

# Wire it in
graph.add_edge("fetch_data", "fetch_sec_filings")
graph.add_edge("fetch_sec_filings", "run_analysis")
```

Ideas for next nodes: SEC filings via EDGAR, options flow via unusual_whales, earnings calendar via Alpha Vantage free tier.

---

## License

MIT
