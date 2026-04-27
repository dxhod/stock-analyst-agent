from langgraph.graph import StateGraph, END
from agents.state import AgentState
from tools import fetch_price_data, fetch_fundamentals, fetch_news, news_to_text
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3,
    streaming=True,
)

# ── Nodes ──────────────────────────────────────────────────────────────────────

def fetch_data(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    try:
        return {
            **state,
            "price_data": fetch_price_data(ticker),
            "fundamentals": fetch_fundamentals(ticker),
            "news": fetch_news(ticker),
            "error": None,
        }
    except Exception as e:
        return {**state, "error": str(e)}

def run_analysis(state: AgentState) -> AgentState:
    if state.get("error"):
        return state

    p = state["price_data"]
    f = state["fundamentals"]
    news_text = news_to_text(state["news"])

    prompt = f"""You are an expert stock analyst. Analyze {p['ticker']} and produce a structured report.

## PRICE DATA
Current: ${p['current_price']} ({p['change_pct']:+.2f}% today)
52w range: ${p['low_52w']} – ${p['high_52w']}
SMA 20/50: {p['sma_20']} / {p['sma_50']}
RSI-14: {p['rsi_14']} | ATR-14: {p['atr_14']}
Relative volume: {p['relative_volume']}x | Signal: {p['cross_signal']}

## FUNDAMENTALS
{f['company_name']} | {f['sector']} | Market cap: {f['market_cap_fmt']}
P/E: {f['pe_trailing']} (fwd {f['pe_forward']}) | PEG: {f['peg_ratio']} | P/B: {f['price_to_book']}
Net margin: {f['net_margin']} | ROE: {f['return_on_equity']} | D/E: {f['debt_to_equity']}
Revenue TTM: {f['revenue_ttm_fmt']} | FCF: {f['free_cash_flow_fmt']}
Analyst: {f['analyst_recommendation']} (n={f['analyst_count']}) | Target: ${f['analyst_target_mean']}

## RECENT NEWS
{news_text}

## REQUIRED OUTPUT SECTIONS
Write each section with the exact heading shown.

### 1. Edge Read
One punchy paragraph. What is the single most important insight about this stock right now? Not a summary — your actual analytical take.

### 2. Technical Picture
HTF/ITF/LTF structure. Key levels, trend, momentum (RSI), volume context.

### 3. Fundamental Snapshot
Valuation vs. sector, quality of earnings, balance sheet health, FCF.

### 4. Catalyst & News Analysis
What's driving price? Upcoming events, macro tailwinds/headwinds.

### 5. Bull Case
3 specific, quantified reasons the stock goes higher.

### 6. Bear Case
3 specific, quantified risks. Be honest.

### 7. Scenario Map
| Scenario | Trigger | Price Target | Probability |
|---|---|---|---|
Fill with Bull / Base / Bear rows.

### 8. Trade Ideas
For each idea: Direction, Entry, Stop, Target, R:R, Timeframe, Invalidation.

### 9. Verdict
One sentence. Bias, conviction level (low/medium/high), and key variable to watch.
"""

    response = llm.invoke(prompt)
    return {**state, "analysis": response.content}

def should_continue(state: AgentState) -> str:
    return "end" if state.get("error") else "analyze"

# ── Graph ──────────────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("fetch_data", fetch_data)
    graph.add_node("run_analysis", run_analysis)

    graph.set_entry_point("fetch_data")
    graph.add_conditional_edges(
        "fetch_data",
        should_continue,
        {"analyze": "run_analysis", "end": END},
    )
    graph.add_edge("run_analysis", END)

    return graph.compile()

agent = build_graph()
