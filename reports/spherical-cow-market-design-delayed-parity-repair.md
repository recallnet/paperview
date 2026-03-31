# Venue-Shaped Delayed Parity Repair

Lead(s): Kristal Soman
Categories: Prediction Markets
Strategy Theme: Cross-Venue Relative Value
Venues: Kalshi, Polymarket, Limitless
Edge Description: Structural price repair delay between matched event markets listed on different venues with different rule surfaces, tick sizes, protection logic, and liquidity regimes. The edge is not generic cross-venue arb; it is the short window where one venue begins repairing toward fair value and the lagging venue remains stale because its local design rules slow convergence.
Null Hypothesis: Cross-venue delayed parity repair in matched prediction markets is too short-lived, too sparse, or too contaminated by market-matching errors to generate returns materially above fees and slippage after accounting for venue-specific execution friction.
🐮 APR: unknown
🐮 Capacity ($M/Year): unknown
🐮 Oppty: unknown
Experiments: unknown
Last edited time: March 31, 2026 11:59 PM
👼: ✅
AI Thesis Eval (0-5): 4 - The thesis is specific and Tradecore-compatible because it uses venues the system already supports and focuses on a concrete repair-timing mechanism rather than generic fragmentation. It is still un-sized because Tradecore does not yet persist the matched, historical cross-venue state needed for an honest spherical-cow estimate.

## Summary

Kalshi, Polymarket, and Limitless can price the same event through visibly different rule surfaces. Tick size, order priority, matching cadence, market protection, and liquidity shape how quickly a stale book repairs after information arrives or after another venue has already moved.

The lane memo called this "venue-shaped delayed parity repair." In Tradecore terms, the spherical cow is a same-event cross-venue convergence strategy that is stricter than the existing identical-market arb: it cares about *repair timing* after a detectable state break, not just static YES/NO mispricing.

This is closest to Tradecore's lead-lag synchronization motif, but with a different causal story. The bet is not just "venue A leads venue B." The bet is "venue B repairs more slowly under some rule states, so a lag that looks noisy in aggregate becomes tradeable once venue state is part of the trigger."

## "Spherical Cow" Opportunity

---

Spherical Cow data

Query 1: Funnel counts

Query 2: Where opportunities die (market mapping stage)

Query 3: Where opportunities die (state-break detection stage)

Query 4: Where opportunities die (execution gate)

Query 5: Repair-window distribution

Query 6: Fill performance

Query 7: Time-series funnel

---

## Spherical Cow Analysis — March 2026 (Tradecore-Supported Prediction Venues)

*Methodology: constrained to Tradecore-supported prediction venues only: Kalshi, Polymarket, and Limitless. The honest first pass would require synchronized matched-market books plus venue-state annotations so repair windows can be measured after a state break. Tradecore currently supports the venues operationally, but does not yet persist enough matched historical cross-venue state to size this motif honestly.*

### Recommendation

**Do not size this yet. First build a state-aware replay dataset for matched Kalshi / Polymarket / Limitless events.**

The current evidence is good enough to justify research, but not good enough to claim APR, capacity, or opportunity count. Tradecore's own lead-lag research notes that cross-venue mappings are not persisted and historical orderbook snapshots are missing or incomplete. Without that foundation, any spherical-cow estimate would be fabricated.

### Detection Funnel

| Stage | n | Notes |
| --- | --- | --- |
| Matched event pairs across venues | unknown | Cross-venue mapping exists at runtime, not as a stable historical research table |
| Historical synchronized books | unknown | Tradecore venue support exists, but historical matched snapshots are not yet available in a research-ready form |
| Detected state breaks | unknown | Requires a repair-state definition, not just raw spread comparisons |
| State breaks with venue asymmetry labels | unknown | Tick-size / protection / rule-state annotations not yet materialized into a replayable dataset |
| Executable delayed-repair windows | unknown | Cannot be estimated honestly without the earlier stages |

### Where the Opportunity Probably Lives

- Kalshi versus Polymarket on same-event markets where one venue updates first and the other still shows stale quotes.
- Kalshi versus Limitless or Polymarket versus Limitless when liquidity asymmetry plus venue design creates a slower repair path on the thinner venue.
- Event windows where local rules matter more: low-liquidity states, near contract resolution, post-news bursts, or other periods where stale books are not immediately competed away.

### What "Viable" Would Look Like

A viable version of this motif would show all of the following:

- A repeatable delay between a state break and a repair on the lagging venue.
- A measurable difference between state-aware triggers and a naive identical-market arb trigger.
- Enough resting or taking liquidity on the lagging venue to enter before repair closes.
- Net edge that survives venue fees, slippage, and stale-quote false positives.

### Why The Unknowns Stay Unknown

Tradecore already has the right venue set, but the necessary research substrate is still missing:

- Cross-venue market mapping is not persisted as a historical research table.
- Historical orderbook snapshots for matched venue pairs are not available in a stable research surface.
- Venue-state annotations needed for this motif, such as repair-state boundary or rule-state tags, do not yet exist in a replayable dataset.

So the correct spherical-cow posture is: **promising thesis, un-sized opportunity**.

### Smallest Honest First Pass

1. Persist matched Kalshi / Polymarket / Limitless event pairs as a research table.
2. Record synchronized top-of-book or depth snapshots at 1-second cadence or finer for those pairs.
3. Define a state break: one venue moves by more than a threshold while the matched venue stays stale inside a reaction window.
4. Add venue-state tags that are observable in practice: spread regime, tick regime, liquidity depth, time-to-resolution bucket.
5. Compare repair-time and fee-adjusted convergence capture for state-aware triggers versus a naive identical-market spread trigger.

### Key Takeaways

1. This motif is Tradecore-compatible because all proposed venues are already supported.
2. It is not the same as plain identical-market arb; the core thesis is *repair timing conditioned on venue state*.
3. The current unknowns are structural, not cosmetic. APR, capacity, and opportunity count are not honest yet.
4. The first pass should be a data and replay study, not an execution launch.

---
