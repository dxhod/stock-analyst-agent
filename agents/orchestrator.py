import json
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

from agents.cache import build_analysis_cache, get_valid_cached_analysis
from agents.language_detector import detect_language
from agents.run_logger import ensure_run_id, log_agent_run
from agents.state import AgentState
from agents.ticker_resolver import normalize_ticker
from prompts.analysis import (
    build_follow_up_prompt,
    build_fundamental_prompt,
    build_intent_prompt,
    build_news_prompt,
    build_summary_prompt,
    build_technical_prompt,
)
from tools import fetch_fundamentals, fetch_news, fetch_price_data, news_to_text

load_dotenv()

_stream_callback = None


def set_stream_callback(callback):
    global _stream_callback
    previous_callback = _stream_callback
    _stream_callback = callback
    return previous_callback


def reset_stream_callback(callback):
    global _stream_callback
    _stream_callback = callback


DEFAULT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
DEFAULT_INTENT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
DEFAULT_SUMMARY_MODEL = "llama-3.3-70b-versatile"


def _invoke_text(
    prompt: str,
    stream_to_ui: bool = False,
    model: str | None = None,
    agent_name: str = "unknown_agent",
    state: AgentState | None = None,
) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is missing. Create a .env file from .env.example and add your Groq API key."
        )

    selected_model = model or os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    llm = ChatGroq(
        model=selected_model,
        api_key=api_key,
        temperature=0.2,
        streaming=True,
    )
    config = None
    if stream_to_ui and _stream_callback:
        config = {"callbacks": [_stream_callback]}

    response = llm.invoke(prompt, config=config)
    log_agent_run(
        agent=agent_name,
        model=selected_model,
        prompt=prompt,
        output=response.content,
        state=state,
    )
    return response.content


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        if start == -1:
            raise

        decoder = json.JSONDecoder()
        parsed, _ = decoder.raw_decode(cleaned[start:])
        return parsed


def validate_intent(state: AgentState) -> AgentState:
    ensure_run_id(state)
    cached_analysis = get_valid_cached_analysis(state.get("cached_analysis"))
    prompt = build_intent_prompt(
        user_query=state["user_query"],
        cached_analysis=cached_analysis,
    )

    try:
        intent_model = os.getenv("GROQ_INTENT_MODEL", DEFAULT_INTENT_MODEL)
        intent = _parse_json(
            _invoke_text(prompt, model=intent_model, agent_name="intent_validator", state=state)
        )
    except Exception as e:
        return {"error": f"Could not validate intent: {e}"}

    route = intent.get("route")
    ticker = normalize_ticker(state["user_query"], intent.get("ticker"))
    language = detect_language(state["user_query"], intent.get("language"))

    if route == "follow_up" and not cached_analysis:
        return {"error": "Follow-up requested, but no valid cached analysis was found."}

    if route == "new_analysis" and not ticker:
        return {
            "error": (
                "I could not identify a valid stock ticker from your request. "
                "Try a ticker like AAPL, TSLA, or NVDA."
            )
        }

    if route not in {"new_analysis", "follow_up"}:
        return {
            "intent": intent,
            "error": "Ask about a stock ticker or company, for example: Analyze Tesla stock.",
        }

    return {
        "intent": intent,
        "run_id": state["run_id"],
        "ticker": ticker or (cached_analysis or {}).get("ticker", ""),
        "language": language,
        "cached_analysis": cached_analysis,
        "error": None,
    }


def route_after_intent(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    if state.get("intent", {}).get("route") == "follow_up":
        return "follow_up"
    return "new_analysis"


def fetch_data(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    try:
        return {
            "run_id": state.get("run_id"),
            "price_data": fetch_price_data(ticker),
            "fundamentals": fetch_fundamentals(ticker),
            "news": fetch_news(ticker),
            "error": None,
        }
    except Exception as e:
        return {"error": str(e)}


def should_analyze(state: AgentState) -> str:
    return "end" if state.get("error") else "analyze"


def fanout_agents(state: AgentState) -> AgentState:
    return {}


def technical_agent(state: AgentState) -> AgentState:
    language = detect_language(state["user_query"], state.get("language"))
    prompt = build_technical_prompt(
        price_data=state["price_data"],
        language=language,
    )
    return {
        "technical_analysis": _invoke_text(prompt, agent_name="technical_agent", state=state)
    }


def fundamental_agent(state: AgentState) -> AgentState:
    language = detect_language(state["user_query"], state.get("language"))
    prompt = build_fundamental_prompt(
        fundamentals=state["fundamentals"],
        language=language,
    )
    return {
        "fundamental_analysis": _invoke_text(prompt, agent_name="fundamental_agent", state=state)
    }


def news_agent(state: AgentState) -> AgentState:
    language = detect_language(state["user_query"], state.get("language"))
    prompt = build_news_prompt(
        ticker=state["ticker"],
        news_text=news_to_text(state["news"]),
        language=language,
    )
    return {
        "news_analysis": _invoke_text(prompt, agent_name="news_agent", state=state)
    }


def summarizer_agent(state: AgentState) -> AgentState:
    language = detect_language(state["user_query"], state.get("language"))
    summary_model = os.getenv("GROQ_SUMMARY_MODEL", DEFAULT_SUMMARY_MODEL)
    prompt = build_summary_prompt(
        user_query=state["user_query"],
        ticker=state["ticker"],
        technical_analysis=state["technical_analysis"],
        fundamental_analysis=state["fundamental_analysis"],
        news_analysis=state["news_analysis"],
        language=language,
    )
    next_state = {
        **state,
        "language": language,
        "analysis": _invoke_text(
            prompt,
            stream_to_ui=True,
            model=summary_model,
            agent_name="summarizer_agent",
            state=state,
        ),
    }
    return {
        "analysis": next_state["analysis"],
        "cached_analysis": build_analysis_cache(next_state),
    }


def follow_up_agent(state: AgentState) -> AgentState:
    cached_analysis = get_valid_cached_analysis(state.get("cached_analysis"))
    if not cached_analysis:
        return {"error": "The previous analysis has expired. Please ask for a new stock analysis."}

    language = detect_language(state["user_query"], state.get("language") or cached_analysis.get("language"))
    prompt = build_follow_up_prompt(
        user_query=state["user_query"],
        cached_analysis=cached_analysis,
        conversation=state.get("conversation", []),
        language=language,
    )
    return {
        "ticker": cached_analysis.get("ticker", ""),
        "analysis": _invoke_text(
            prompt,
            stream_to_ui=True,
            agent_name="follow_up_agent",
            state=state,
        ),
        "cached_analysis": cached_analysis,
    }


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("validate_intent", validate_intent)
    graph.add_node("fetch_data", fetch_data)
    graph.add_node("fanout_agents", fanout_agents)
    graph.add_node("technical_agent", technical_agent)
    graph.add_node("fundamental_agent", fundamental_agent)
    graph.add_node("news_agent", news_agent)
    graph.add_node("summarizer_agent", summarizer_agent)
    graph.add_node("follow_up_agent", follow_up_agent)

    graph.set_entry_point("validate_intent")
    graph.add_conditional_edges(
        "validate_intent",
        route_after_intent,
        {
            "new_analysis": "fetch_data",
            "follow_up": "follow_up_agent",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "fetch_data",
        should_analyze,
        {
            "analyze": "fanout_agents",
            "end": END,
        },
    )
    graph.add_edge("fanout_agents", "technical_agent")
    graph.add_edge("fanout_agents", "fundamental_agent")
    graph.add_edge("fanout_agents", "news_agent")
    graph.add_edge(
        ["technical_agent", "fundamental_agent", "news_agent"],
        "summarizer_agent",
    )
    graph.add_edge("summarizer_agent", END)
    graph.add_edge("follow_up_agent", END)

    return graph.compile()


agent = build_graph()
