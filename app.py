import streamlit as st
from langchain_core.callbacks import BaseCallbackHandler

from agents import agent, reset_stream_callback, set_stream_callback
from agents.cache import CACHE_TTL, get_valid_cached_analysis, now_utc

st.set_page_config(
    page_title="Stock Analyst Agent",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1180px;
            padding-top: 4.25rem;
            padding-bottom: 3rem;
        }
        [data-testid="stHeader"] {
            background: transparent;
        }
        .stApp,
        .block-container,
        [data-testid="stVerticalBlock"],
        [data-testid="column"],
        [data-testid="stMarkdownContainer"] {
            caret-color: transparent;
            cursor: default;
            user-select: none;
        }
        a[href^="#"],
        a.anchor-link {
            display: none !important;
        }
        .hero-title {
            margin: 0;
            text-align: center;
            font-size: 2.65rem;
            line-height: 1.15;
            font-weight: 800;
            letter-spacing: 0;
            cursor: default;
            user-select: none;
        }
        .hero-subtitle {
            margin-top: 1.05rem;
            margin-bottom: 1.35rem;
            text-align: center;
            color: rgba(250, 250, 250, 0.58);
            font-size: 0.88rem;
            font-weight: 700;
            letter-spacing: 0;
            cursor: default;
            user-select: none;
        }
        h1 {
            text-align: center;
        }
        div[data-testid="stCaptionContainer"] {
            text-align: center;
        }
        div[data-testid="stForm"] {
            border: 1px solid rgba(250, 250, 250, 0.14);
            border-radius: 28px;
            padding: 0.75rem 0.85rem;
            background: rgba(255, 255, 255, 0.07);
        }
        div[data-testid="stTextInput"] input {
            caret-color: auto;
            min-height: 52px;
            border-radius: 20px;
            border: 0;
            background: transparent;
            font-size: 1.02rem;
            cursor: text;
            user-select: text;
        }
        div[data-testid="stTextInput"] [data-baseweb="input"],
        div[data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
            border-color: transparent !important;
            box-shadow: none !important;
            outline: none !important;
        }
        div[data-testid="stTextInput"] input:focus {
            box-shadow: none;
            outline: none;
        }
        div[data-testid="InputInstructions"] {
            display: none;
        }
        div[data-testid="stFormSubmitButton"] button {
            width: 48px;
            min-width: 48px;
            height: 48px;
            min-height: 48px;
            border-radius: 999px;
            padding: 0;
            font-size: 1.35rem;
            font-weight: 800;
            cursor: pointer;
        }
        div[data-testid="stButton"] button {
            min-height: 42px;
            border-radius: 999px;
            font-weight: 600;
            cursor: pointer;
        }
        [data-testid="stChatMessage"] {
            border-radius: 8px;
            padding: 0.35rem 0.1rem;
            user-select: text;
        }
        [data-testid="stChatMessage"] *,
        [data-testid="stChatMessageContent"] {
            caret-color: transparent;
            user-select: text;
        }
        [data-testid="stChatMessageContent"] h1,
        [data-testid="stChatMessageContent"] h2,
        [data-testid="stChatMessageContent"] h3 {
            letter-spacing: 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "conversation_updated_at" not in st.session_state:
    st.session_state.conversation_updated_at = None
if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = None
if "user_query_input" not in st.session_state:
    st.session_state.user_query_input = ""
if "pending_query" not in st.session_state:
    st.session_state.pending_query = ""


def submit_query():
    st.session_state.pending_query = st.session_state.user_query_input.strip()
    st.session_state.user_query_input = ""


def set_example_query(text: str):
    st.session_state.user_query_input = text


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


def render_header():
    left, center, right = st.columns([1, 2.35, 1])
    with center:
        st.markdown(
            """
            <div class="hero-title">Stock Analyst Agent</div>
            <div class="hero-subtitle">MULTI-AGENT EQUITY RESEARCH</div>
            """,
            unsafe_allow_html=True,
        )


def render_composer():
    left, center, right = st.columns([0.35, 3.3, 0.35])
    with center:
        with st.form("query_form", clear_on_submit=False):
            input_col, send_col = st.columns([12, 1])
            with input_col:
                st.text_input(
                    "Ask about a stock",
                    placeholder="Ask about a stock or company",
                    label_visibility="collapsed",
                    key="user_query_input",
                )
            with send_col:
                run = st.form_submit_button("↑", type="primary", on_click=submit_query)

        _, example_col_1, example_col_2, _ = st.columns([0.3, 1.3, 1.3, 0.3])
        with example_col_1:
            st.button(
                "Analyze Tesla stock",
                use_container_width=True,
                on_click=set_example_query,
                args=("Analyze Tesla stock",),
            )
        with example_col_2:
            st.button(
                "Compare NVDA and Apple risks",
                use_container_width=True,
                on_click=set_example_query,
                args=("Compare NVDA and Apple risks",),
            )

    return run


def render_conversation(streaming: bool = False):
    message_count = len(st.session_state.conversation)
    heading_col, count_col = st.columns([5, 1])
    heading_col.subheader("Conversation")
    count_col.caption(f"{message_count} messages")

    with st.container(height=560, border=True):
        for message in st.session_state.conversation:
            role = "user" if message["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.markdown(message["content"])

        if streaming:
            with st.chat_message("assistant"):
                return st.empty()

    return None


render_header()
run = render_composer()

if st.session_state.conversation:
    clear_col, _ = st.columns([1, 6])
    with clear_col:
        if st.button("Clear", use_container_width=True):
            st.session_state.conversation = []
            st.session_state.conversation_updated_at = None
            st.session_state.analysis_cache = None
            st.rerun()

query = st.session_state.pending_query
conversation_rendered = False

if query:
    st.session_state.pending_query = ""
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
