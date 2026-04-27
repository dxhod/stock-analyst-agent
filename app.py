import streamlit as st
from agents import agent

st.set_page_config(
    page_title="Stock Analyst Agent",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Stock Analyst Agent")
st.caption("Powered by LangGraph · Groq · yfinance")

# ── Input ──────────────────────────────────────────────────────────────────────

col1, col2 = st.columns([3, 1])
with col1:
    ticker = st.text_input(
        "Ticker symbol",
        placeholder="AAPL, NVDA, TSLA...",
        label_visibility="collapsed",
    )
with col2:
    run = st.button("Analyze", type="primary", use_container_width=True)

# ── Run ────────────────────────────────────────────────────────────────────────

if run and ticker:
    ticker = ticker.strip().upper()

    with st.status(f"Fetching data for {ticker}...", expanded=True) as status:
        st.write("📡 Pulling price data, fundamentals, news...")

        state = agent.invoke({"ticker": ticker, "analysis": "", "error": None})

        if state.get("error"):
            status.update(label="Error", state="error")
            st.error(state["error"])
            st.stop()

        status.update(label="Data fetched — running analysis...", state="running")
        st.write("🤖 LLM analyzing...")
        status.update(label="Done", state="complete", expanded=False)

    # ── Metrics row ────────────────────────────────────────────────────────────
    p = state["price_data"]
    f = state["fundamentals"]

    st.divider()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Price", f"${p['current_price']}", f"{p['change_pct']:+.2f}%")
    m2.metric("Market Cap", f['market_cap_fmt'])
    m3.metric("P/E (fwd)", f['pe_forward'])
    m4.metric("RSI-14", p['rsi_14'])
    m5.metric(
        "Analyst",
        (f['analyst_recommendation'] or "—").upper(),
        f"n={f['analyst_count']}",
    )

    st.divider()

    # ── Analysis output ────────────────────────────────────────────────────────
    st.markdown(state["analysis"])

    # ── Download ───────────────────────────────────────────────────────────────
    st.divider()
    st.download_button(
        label="⬇ Download report (Markdown)",
        data=state["analysis"],
        file_name=f"{ticker}_analysis.md",
        mime="text/markdown",
    )

elif run and not ticker:
    st.warning("Enter a ticker symbol first.")
