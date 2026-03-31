# Settlement-Lag / Resolution-Friction Timing

Lead(s): Kristal Soman
Categories: Prediction Markets, Perpetuals, Spot Crypto
Strategy Theme: Resolution-State Relative Value
Venues: Kalshi, Polymarket, Limitless, Hyperliquid, Coinbase, Binance
Edge Description: Economic execution can move ahead of legal, collateral, inventory, or transfer resolution. The edge is a timing seam where price, hedge, or inventory pressure reacts before the relevant venue state fully synchronizes across execution, collateral, or settlement surfaces.
Null Hypothesis: Apparent settlement or resolution timing dislocations across supported venues are too rare, too noisy, or too dependent on unobservable post-trade state to generate returns materially above fees after execution friction and carry costs.
🐮 APR: unknown
🐮 Capacity ($M/Year): unknown
🐮 Oppty: unknown
Experiments: unknown
Last edited time: March 31, 2026 11:59 PM
👼: ✅
AI Thesis Eval (0-5): 3 - The thesis is coherent and maps to Tradecore-supported venues, but honest sizing is still unavailable because the required post-trade or resolution-state history is not yet a persisted research surface in Tradecore.

## Summary

The lane memo described a seam between economic execution and legal or operational resolution. In Tradecore terms, the spherical cow is not a generic basis trade. It is a strategy that watches for moments when the trade can be priced and hedged faster than the associated collateral, transfer, liquidation, or inventory state can synchronize.

This is potentially relevant across several supported venue families:

- prediction venues where market rules and event-resolution mechanics differ
- perps versus spot where hedge pressure can arrive before inventory or transfer state catches up
- on-chain or hybrid venues where liquidation or collateral state is more explicit than in mature centralized markets

The key constraint is honesty: Tradecore supports the venues, but does not yet expose a stable historical table for the relevant settlement or resolution-state clocks. So this memo names the likely opportunity, but does not pretend to size it.

## "Spherical Cow" Opportunity

---

Spherical Cow data

Query 1: Funnel counts

Query 2: Where opportunities die (state-detection stage)

Query 3: Where opportunities die (execution gate)

Query 4: Where opportunities die (hedge / transfer gate)

Query 5: Edge distribution

Query 6: Fill performance

Query 7: Time-series funnel

---

## Spherical Cow Analysis — March 2026 (Tradecore-Supported Venue Families)

*Methodology: constrained to supported venues only: Kalshi, Polymarket, Limitless, Hyperliquid, Coinbase, and Binance. The honest first pass requires historical alignment between executable price state and the relevant resolution state, such as event resolution, collateral or liquidation state, transfer latency, or hedge inventory synchronization. Tradecore does not yet persist that full state history in a research-ready form.*

### Recommendation

**Do not size this yet. First define one concrete resolution-state seam and build the smallest replay dataset for it.**

The strongest immediate candidate is not all six venues at once. It is one narrow family where the resolution clock is visible enough to measure. The cleanest possibilities are:

- Polymarket or Limitless liquidation or collateral stress versus spot or perp hedge state
- Hyperliquid perp moves versus spot hedge or transfer state on Coinbase / Binance
- Prediction venue event-resolution or inventory pressure windows where one venue repairs earlier than another

### Detection Funnel

| Stage | n | Notes |
| --- | --- | --- |
| Candidate venue families | unknown | The venue set is known, but the concrete resolution-state seam must be chosen first |
| Historical price + hedge state | unknown | Tradecore supports venue ingestion, but not a unified research table for this seam |
| Historical resolution-state labels | unknown | Liquidation, transfer, collateral, or event-resolution clocks are not yet materialized as a replay dataset here |
| Detected delayed-resolution windows | unknown | Cannot be estimated honestly without the earlier stages |
| Executable windows surviving fees and carry | unknown | Also unknown without matched state history |

### Where the Opportunity Probably Lives

- Hyperliquid perp dislocations that appear before spot hedge or transfer state fully synchronizes on Coinbase or Binance.
- Prediction venue pairs where price moves quickly but venue-specific event-resolution or inventory mechanics slow final repair.
- Thin or immature venues where liquidation and collateral mechanics are visible enough that the delay state can be observed rather than inferred.

### What "Viable" Would Look Like

A viable version of this motif would show:

- a repeatable lag between price adjustment and the relevant resolution-state adjustment
- an executable hedge or unwind during that lag
- net edge that survives fees, slippage, financing, and carry
- a resolution-state variable that adds signal beyond plain spread, basis, or volatility

### Why The Unknowns Stay Unknown

Tradecore has the venue support, but not yet the historical research substrate for this motif:

- no persisted, unified resolution-state history across the candidate venue families
- no canonical replay surface for collateral, liquidation, transfer, or event-resolution clocks
- no honest funnel yet for how often delayed-resolution windows survive into executable trades

So the correct spherical-cow posture is: **supported venues, credible seam, un-sized opportunity**.

### Smallest Honest First Pass

1. Pick one concrete seam, not all venue families at once.
2. Persist the relevant price state and the relevant resolution state into one replayable dataset.
3. Define a delayed-resolution event: price or hedge state moves first, resolution state catches up later.
4. Measure how long the lag lasts and whether it leaves executable room after fees and carry.
5. Compare the state-aware trigger against a price-only baseline.

### Key Takeaways

1. This motif belongs in Tradecore because the supported venues span prediction, perps, and spot.
2. It should not be treated as a generic spread or basis strategy.
3. The main blocker is not theory; it is the lack of persisted resolution-state history.
4. APR, capacity, and opportunity count remain honestly unknown until that history exists.

---
