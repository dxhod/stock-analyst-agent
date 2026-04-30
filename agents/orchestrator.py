import json
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

from agents.cache import build_analysis_cache, get_valid_cached_analysis
from agents.language_detector import detect_language
from agents.run_logger import ensure_run_id, log_agent_run
from agents.state import AgentState
from agents.ticker_resolver import normalize_tickers
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
DEFAULT_SUMMARY_MODEL = "openai/gpt-oss-120b"
DEFAULT_SUMMARY_FALLBACK_MODELS = (   
    "llama-3.3-70b-versatile,"
    "meta-llama/llama-4-scout-17b-16e-instruct"
)


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _env_list(name: str, default: str) -> list[str]:
    value = os.getenv(name) or os.getenv(name.rstrip("S")) or default
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return "rate_limit" in text or "rate limit" in text or "429" in text


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

    selected_model = model or _env("GROQ_MODEL", DEFAULT_MODEL)
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
        intent_model = _env("GROQ_INTENT_MODEL", DEFAULT_INTENT_MODEL)
        intent = _parse_json(
            _invoke_text(prompt, model=intent_model, agent_name="intent_validator", state=state)
        )
    except Exception as e:
        return {"error": f"Could not validate intent: {e}"}

    route = intent.get("route")
    query_tickers = normalize_tickers(state["user_query"])
    model_tickers = normalize_tickers(
        "",
        raw_ticker=intent.get("ticker"),
        raw_tickers=intent.get("tickers") or [],
    )
    tickers = query_tickers or model_tickers
    language = detect_language(state["user_query"], intent.get("language"))
    cached_tickers = (cached_analysis or {}).get("tickers") or (
        [(cached_analysis or {}).get("ticker")] if (cached_analysis or {}).get("ticker") else []
    )

    if query_tickers and (
        not cached_tickers or any(ticker not in cached_tickers for ticker in query_tickers)
    ):
        route = "new_analysis"
        intent["route"] = route
    elif cached_analysis and not tickers and route != "unknown":
        route = "follow_up"
        intent["route"] = route
        tickers = cached_tickers

    if route == "follow_up" and not cached_analysis:
        return {"error": "Follow-up requested, but no valid cached analysis was found."}

    if route == "new_analysis" and not tickers:
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
        "ticker": (tickers[0] if tickers else (cached_analysis or {}).get("ticker", "")),
        "tickers": tickers or cached_tickers,
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
    tickers = state.get("tickers") or [state["ticker"]]
    try:
        price_data_by_ticker = {}
        fundamentals_by_ticker = {}
        news_by_ticker = {}
        for ticker in tickers:
            price_data_by_ticker[ticker] = fetch_price_data(ticker)
            fundamentals_by_ticker[ticker] = fetch_fundamentals(ticker)
            news_by_ticker[ticker] = fetch_news(ticker)

        primary_ticker = tickers[0]
        return {
            "run_id": state.get("run_id"),
            "ticker": primary_ticker,
            "tickers": tickers,
            "price_data": price_data_by_ticker[primary_ticker],
            "price_data_by_ticker": price_data_by_ticker,
            "fundamentals": fundamentals_by_ticker[primary_ticker],
            "fundamentals_by_ticker": fundamentals_by_ticker,
            "news": news_by_ticker[primary_ticker],
            "news_by_ticker": news_by_ticker,
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
    price_data = state.get("price_data_by_ticker") or state["price_data"]
    prompt = build_technical_prompt(
        price_data=price_data,
        language=language,
    )
    return {
        "technical_analysis": _invoke_text(prompt, agent_name="technical_agent", state=state)
    }


def fundamental_agent(state: AgentState) -> AgentState:
    language = detect_language(state["user_query"], state.get("language"))
    fundamentals = state.get("fundamentals_by_ticker") or state["fundamentals"]
    prompt = build_fundamental_prompt(
        fundamentals=fundamentals,
        language=language,
    )
    return {
        "fundamental_analysis": _invoke_text(prompt, agent_name="fundamental_agent", state=state)
    }


def news_agent(state: AgentState) -> AgentState:
    language = detect_language(state["user_query"], state.get("language"))
    tickers = state.get("tickers") or [state["ticker"]]
    news_by_ticker = state.get("news_by_ticker")
    if news_by_ticker:
        news_text = "\n\n".join(
            f"## {ticker}\n{news_to_text(news_by_ticker.get(ticker, []))}" for ticker in tickers
        )
    else:
        news_text = news_to_text(state["news"])
    prompt = build_news_prompt(
        ticker=", ".join(tickers),
        news_text=news_text,
        language=language,
    )
    return {
        "news_analysis": _invoke_text(prompt, agent_name="news_agent", state=state)
    }


def summarizer_agent(state: AgentState) -> AgentState:
    language = detect_language(state["user_query"], state.get("language"))
    summary_model = _env("GROQ_SUMMARY_MODEL", DEFAULT_SUMMARY_MODEL)
    fallback_models = _env_list("GROQ_SUMMARY_FALLBACK_MODELS", DEFAULT_SUMMARY_FALLBACK_MODELS)
    tickers = state.get("tickers") or [state["ticker"]]
    prompt = build_summary_prompt(
        user_query=state["user_query"],
        ticker=", ".join(tickers),
        technical_analysis=state["technical_analysis"],
        fundamental_analysis=state["fundamental_analysis"],
        news_analysis=state["news_analysis"],
        language=language,
    )
    try:
        analysis = _invoke_text(
            prompt,
            stream_to_ui=True,
            model=summary_model,
            agent_name="summarizer_agent",
            state=state,
        )
    except Exception as e:
        if not _is_rate_limit_error(e):
            raise
        last_error = e
        analysis = None
        for fallback_model in fallback_models:
            if fallback_model == summary_model:
                continue
            try:
                analysis = _invoke_text(
                    prompt,
                    stream_to_ui=True,
                    model=fallback_model,
                    agent_name=f"summarizer_agent_fallback:{fallback_model}",
                    state=state,
                )
                break
            except Exception as fallback_error:
                if not _is_rate_limit_error(fallback_error):
                    raise
                last_error = fallback_error
        if analysis is None:
            raise last_error

    next_state = {
        **state,
        "language": language,
        "analysis": analysis,
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
        "tickers": cached_analysis.get("tickers") or ([cached_analysis.get("ticker")] if cached_analysis.get("ticker") else []),
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
