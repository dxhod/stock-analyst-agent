"""
Analysis prompt. Edit this file to change the report structure.
"""

def build_prompt(p: dict, f: dict, news_text: str) -> str:
    return f"""You are an expert stock analyst. Analyze {p['ticker']} and produce a structured investment report.
Be specific, data-driven, and direct. Avoid generic statements.

## PRICE DATA
Current: ${p['current_price']} ({p['change_pct']:+.2f}% today)
52w range: ${p['low_52w']} - ${p['high_52w']} | Distance from 52w high: {p['pct_from_52w_high']}%
SMA 20/50: {p['sma_20']} / {p['sma_50']}
RSI-14: {p['rsi_14']} | ATR-14: {p['atr_14']}
Relative volume: {p['relative_volume']}x | Signal: {p['cross_signal']}

## FUNDAMENTALS
{f['company_name']} | {f['sector']} | {f['industry']}
Market cap: {f['market_cap_fmt']} | Beta: {f['beta']}
P/E: {f['pe_trailing']} (fwd {f['pe_forward']}) | PEG: {f['peg_ratio']} | P/B: {f['price_to_book']}
EV/EBITDA: {f['ev_to_ebitda']} | EV/Revenue: {f['ev_to_revenue']}
Net margin: {f['net_margin']} | Operating margin: {f['operating_margin']}
ROE: {f['return_on_equity']} | D/E: {f['debt_to_equity']} | Current ratio: {f['current_ratio']}
Revenue TTM: {f['revenue_ttm_fmt']} | FCF: {f['free_cash_flow_fmt']}
Analyst: {f['analyst_recommendation']} (n={f['analyst_count']}) | Target: ${f['analyst_target_mean']}

## RECENT NEWS
{news_text}

---

## REQUIRED OUTPUT SECTIONS

### 1. Edge Read
One punchy paragraph. Your actual analytical take, not a summary.

### 2. Technical Picture
HTF/ITF/LTF structure. Key support and resistance with exact prices. RSI and volume context.

### 3. Fundamental Snapshot
Valuation vs. sector peers. Earnings quality. Balance sheet health. FCF.

### 4. Catalyst and News Analysis
What is driving price action? Upcoming events, macro tailwinds and headwinds.

### 5. Bull Case
3 specific, quantified reasons the stock goes higher. Include upside targets.

### 6. Bear Case
3 specific, quantified risks. What could go wrong and by how much?

### 7. Scenario Map
| Scenario | Trigger | Price Target | Probability |
|----------|---------|--------------|-------------|
| Bull     |         |              |             |
| Base     |         |              |             |
| Bear     |         |              |             |

### 8. Trade Ideas
1-2 ideas. For each: Direction, Entry, Stop, Target, R:R, Timeframe, Invalidation.

### 9. Verdict
One sentence. Bias (bullish/bearish/neutral), conviction (low/medium/high), key variable to watch.
"""
