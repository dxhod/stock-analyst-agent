import streamlit as st
from langchain_core.callbacks import BaseCallbackHandler

from agents import agent, reset_stream_callback, set_stream_callback
from agents.cache import CACHE_TTL, get_valid_cached_analysis, now_utc

st.set_page_config(
    page_title="Stock Analyst Agent",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Stock Analyst Agent")
st.caption("Multi-agent workflow powered by LangGraph, Groq, and yfinance")

if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "conversation_updated_at" not in st.session_state:
    st.session_state.conversation_updated_at = None
if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = None

conversation_updated_at = st.session_state.conversation_updated_at
if conversation_updated_at and now_utc() - conversation_updated_at > CACHE_TTL:
    st.session_state.conversation = []
    st.session_state.conversation_updated_at = None
    st.session_state.analysis_cache = None

valid_cache = get_valid_cached_analysis(st.session_state.analysis_cache)
if not valid_cache:
    st.session_state.analysis_cache = None


class StreamlitTokenCallback(BaseCallbackHandler):
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.tokens = []

    def on_llm_new_token(self, token: str, **kwargs):
        self.tokens.append(token)
        self.placeholder.markdown("".join(self.tokens) + "▌")

    def finish(self, final_text: str):
        self.placeholder.markdown(final_text)


def render_conversation(streaming: bool = False):
    st.divider()
    st.subheader("Conversation")

    with st.container(height=520, border=True):
        for message in st.session_state.conversation:
            role = "user" if message["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.markdown(message["content"])

        if streaming:
            with st.chat_message("assistant"):
                return st.empty()

    return None


with st.form("query_form", clear_on_submit=True):
    col1, col2 = st.columns([6, 1])
    with col1:
        user_query = st.text_input(
            "Ask about a stock",
            placeholder="Analyze Tesla stock, compare NVDA risks, what is the bull case?",
            label_visibility="collapsed",
        )
    with col2:
        run = st.form_submit_button("Ask", type="primary", use_container_width=True)

if valid_cache:
    st.caption(f"Active analysis: {valid_cache.get('ticker')}")

query = user_query.strip()
conversation_rendered = False

if run and query:
    prior_conversation = list(st.session_state.conversation)
    st.session_state.conversation.append({"role": "user", "content": query})
    assistant_placeholder = render_conversation(streaming=True)
    conversation_rendered = True

    stream_callback = StreamlitTokenCallback(assistant_placeholder)
    previous_callback = set_stream_callback(stream_callback)

    with st.status("Analyzing request...", expanded=True) as status:
        try:
            state = agent.invoke(
                {
                    "user_query": query,
                    "conversation": prior_conversation,
                    "cached_analysis": st.session_state.analysis_cache,
                    "analysis": "",
                    "error": None,
                }
            )
        finally:
            reset_stream_callback(previous_callback)

        if state.get("error"):
            status.update(label="Error", state="error")
            st.error(state["error"])
            st.stop()

        status.update(label="Done", state="complete", expanded=False)

    st.session_state.analysis_cache = state.get("cached_analysis")
    stream_callback.finish(state["analysis"])
    st.session_state.conversation.append({"role": "assistant", "content": state["analysis"]})
    st.session_state.conversation_updated_at = now_utc()

elif run:
    st.warning("Ask a question or enter a ticker/company name first.")

if st.session_state.conversation and not conversation_rendered:
    render_conversation()
