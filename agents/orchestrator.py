from langgraph.graph import StateGraph, END
from agents.state import AgentState
from prompts.analysis import build_prompt
from tools import fetch_price_data, fetch_fundamentals, fetch_news, news_to_text
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

def run_analysis(state: AgentState) -> AgentState:
    if state.get("error"):
        return state
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

    prompt = build_prompt(p, f, news_text, state.get("language", "English"))
    print("\n" + "="*60)
    print("PROMPT SENT TO LLM:")
    print("="*60)
    print(prompt)
    print("="*60 + "\n")

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
