"""
Quick smoke test — run this first to verify data tools work.
Usage: python test_tools.py AAPL
"""

import sys
import json
from tools import fetch_price_data, fetch_fundamentals, fetch_news, news_to_text

ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"

print(f"\n{'='*50}")
print(f"  Testing tools for: {ticker.upper()}")
print(f"{'='*50}\n")

# ── Price data ──────────────────────────────────────────────────────────────────
print("▶ fetch_price_data ...")
try:
    price = fetch_price_data(ticker)
    print(f"  Current price : ${price['current_price']}")
    print(f"  Change (1d)   : {price['change_pct']:+.2f}%")
    print(f"  RSI-14        : {price['rsi_14']}")
    print(f"  SMA 20/50/200 : {price['sma_20']} / {price['sma_50']} / {price['sma_200']}")
    print(f"  Cross signal  : {price['cross_signal']}")
    print(f"  Rel. volume   : {price['relative_volume']}x")
    print("  ✓ OK\n")
except Exception as e:
    print(f"  ✗ FAILED: {e}\n")
    price = None

# ── Fundamentals ────────────────────────────────────────────────────────────────
print("▶ fetch_fundamentals ...")
try:
    fund = fetch_fundamentals(ticker)
    print(f"  Company       : {fund['company_name']}")
    print(f"  Sector        : {fund['sector']} / {fund['industry']}")
    print(f"  Market cap    : {fund['market_cap_fmt']}")
    print(f"  P/E (tr/fwd)  : {fund['pe_trailing']} / {fund['pe_forward']}")
    print(f"  Net margin    : {fund['net_margin']}")
    print(f"  Analyst rec.  : {fund['analyst_recommendation']} (n={fund['analyst_count']})")
    print("  ✓ OK\n")
except Exception as e:
    print(f"  ✗ FAILED: {e}\n")
    fund = None

# ── News ────────────────────────────────────────────────────────────────────────
print("▶ fetch_news ...")
try:
    news = fetch_news(ticker, max_items=5)
    print(f"  Items fetched : {len(news)}")
    for item in news[:3]:
        print(f"  [{item['days_ago']}d] {item['source']}: {item['title'][:70]}")
    print("  ✓ OK\n")
except Exception as e:
    print(f"  ✗ FAILED: {e}\n")
    news = []

print("All checks done. Ready for next step: agents/")
