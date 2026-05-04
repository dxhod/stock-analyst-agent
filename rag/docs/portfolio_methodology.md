# Portfolio Builder Methodology

The Portfolio Builder creates stock and ETF allocations from structured user preferences. The engine is deterministic: it chooses tickers, scores candidates, and assigns weights in code. The language model may explain the finished result, but it must not change tickers, weights, scores, cash allocation, or dollar amounts.

Core preferences:

- Investment amount controls dollar allocations.
- Holdings count controls the number of portfolio lines, including cash if selected.
- Risk controls concentration caps and the balance between growth/momentum and quality/risk.
- Horizon is used as explanation context and can later affect scoring weights.
- Style controls scoring weights: Growth, Value, Dividend, Quality, Balanced, Defensive.
- ETF preference controls the share of ETFs selected before stocks.
- Cash buffer reserves part of the portfolio as dry powder.
- Overweight sectors receive priority in candidate selection and a modest score boost.
- Avoid sectors are filtered or penalized.

The default portfolio construction model is core-satellite:

- ETFs can serve as broad core exposure.
- High-scoring stocks serve as satellite positions.
- Conservative portfolios receive lower concentration.
- Aggressive portfolios allow higher concentration and more growth/momentum exposure.
- Cash buffers reduce investable equity allocation pro rata.

The result is informational only and is not financial advice.
