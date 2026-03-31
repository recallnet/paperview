# Rule-Sensitive Toxic-Flow Filters

Lead(s): Kristal Soman
Categories: Prediction Markets, Perpetuals, Spot Crypto
Strategy Theme: Venue-State Flow Filtering
Venues: Kalshi, Polymarket, Limitless, Hyperliquid, Coinbase, Binance
Edge Description: Toxic or manipulative flow should become more predictable when venue rules expose it. The edge is not generic informed-flow detection; it is a venue-state filter that turns cancellations, sweeps, imbalance bursts, or queue pressure into better signals only in specific rule regimes.
Null Hypothesis: Venue-conditioned toxic-flow signatures across supported venues are too noisy, too dependent on unobservable participant labels, or too unstable across market states to generate returns materially above fees and slippage.
🐮 APR: unknown
🐮 Capacity ($M/Year): unknown
🐮 Oppty: unknown
Experiments: unknown
Last edited time: March 31, 2026 11:59 PM
👼: ✅
AI Thesis Eval (0-5): 4 - The thesis maps well to Tradecore because the platform already supports orderbook-driven venues where cancellation bursts, sweeps, and imbalance states are observable. The unknowns are correctly left unknown because Tradecore does not yet have a persisted research surface for venue-state toxicity outcomes across these venues.

## Summary

The lane memo argued that toxic or manipulative flow becomes more repeatable when interpreted through venue-state and rule constraints. In Tradecore terms, the spherical cow is a filtering strategy: do not treat every cancellation burst, sweep, or imbalance spike as toxic. Treat it as potentially toxic only inside specific venue states.

This is relevant across supported venue families:

- prediction venues where rule surfaces and liquidity are thin enough that visible behavior may be more diagnostic
- perps and spot venues where queue pressure, sweep intensity, or imbalance reacts differently under different venue-state conditions

The key restriction is honesty. Tradecore supports the venues, but it does not yet expose a stable historical research table that joins venue state, flow features, and realized adverse-selection outcomes. So the strategy thesis is credible, but not honestly sized.

## "Spherical Cow" Opportunity

---

Spherical Cow data

Query 1: Funnel counts

Query 2: Where opportunities die (state segmentation stage)

Query 3: Where opportunities die (signal-ranking stage)

Query 4: Where opportunities die (execution gate)

Query 5: Edge distribution

Query 6: Fill performance

Query 7: Time-series funnel

---

## Spherical Cow Analysis — March 2026 (Tradecore-Supported Orderbook Venues)

*Methodology: constrained to supported venues only: Kalshi, Polymarket, Limitless, Hyperliquid, Coinbase, and Binance. The honest first pass requires historical joins between flow signatures, venue-state tags, and realized adverse-selection or markout outcomes. Tradecore does not yet persist that combined research surface in a way that supports honest sizing.*

### Recommendation

**Do not size this yet. First build one venue-state toxicity replay table on a single venue family.**

The first pass should not try to solve all venues at once. It should pick one family with visible orderbook structure and enough flow activity to support repeated tests, then ask whether venue-state conditioning improves toxicity prediction over a baseline flow classifier.

### Detection Funnel

| Stage | n | Notes |
| --- | --- | --- |
| Candidate flow events | unknown | Supported venues exist, but the historical replay surface is not yet joined across features and outcomes |
| Events with venue-state tags | unknown | Tick regime, queue state, protection state, or liquidity regime are not yet materialized as a canonical research table |
| Events with realized adverse-selection labels | unknown | Tradecore has execution and venue plumbing, but not an honest cross-venue toxicity research ledger |
| Filtered toxic-flow windows | unknown | Cannot be estimated honestly without the earlier stages |
| Executable windows surviving fees and slippage | unknown | Also unknown without matched signal and outcome history |

### Where the Opportunity Probably Lives

- Prediction markets where thin books make cancellation bursts or sweep patterns more interpretable than in deeper venues.
- Hyperliquid or centralized crypto books where queue pressure or imbalance spikes may mean different things under different liquidity states.
- Periods where venue-state changes are visible, such as shifts in spread, queue depth, time-to-resolution, or volatility regime.

### What "Viable" Would Look Like

A viable version of this motif would show:

- measurable predictive lift from adding venue-state conditioning to a baseline flow-toxicity model
- enough signal persistence to act before the book fully reprices
- better execution quality or avoided adverse selection from filtering bad states
- stability across multiple time periods instead of one narrow regime

### Why The Unknowns Stay Unknown

Tradecore has the supported venues, but not the fully joined research surface this motif needs:

- no canonical replay table joining flow events, venue-state tags, and realized adverse-selection outcomes
- no honest historical funnel for how many venue-state toxicity signals survive into tradeable opportunities
- no stable sizing basis for APR, capacity, or opportunity count

So the correct spherical-cow posture is: **credible filtering thesis, un-sized opportunity**.

### Smallest Honest First Pass

1. Pick one venue family with visible orderbook state.
2. Persist flow events, venue-state tags, and short-horizon markout or adverse-selection outcomes into one research table.
3. Build a baseline classifier from cancellations, sweeps, and imbalance only.
4. Add venue-state interactions and compare predictive lift.
5. Check whether the improved filter actually changes execution outcomes rather than just offline classification metrics.

### Key Takeaways

1. This motif belongs in Tradecore because all required venue families are already supported.
2. The real edge is venue-conditioned filtering, not generic toxicity detection.
3. The blocker is missing joined research history, not lack of a thesis.
4. APR, capacity, and opportunity count remain honestly unknown until that replay surface exists.

---
