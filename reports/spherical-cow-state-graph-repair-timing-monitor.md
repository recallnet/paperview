# State-Graph Repair Timing Monitor

Lead(s): Kristal Soman
Categories: Prediction Markets, Perpetuals, Spot Crypto
Strategy Theme: Graph-Aware Relative Value
Venues: Kalshi, Polymarket, Limitless, Hyperliquid, Coinbase, Binance
Edge Description: Linked markets should be treated as a state graph whose inconsistencies repair on different clocks. The edge is not a single spread or pair trade; it is the timing pattern of which related prices, implied states, or hedge links lag and which repair first.
Null Hypothesis: Graph-aware repair timing across supported venues does not add enough predictive value beyond ordinary pairwise spreads or lead-lag effects to generate returns materially above fees and slippage.
🐮 APR: unknown
🐮 Capacity ($M/Year): unknown
🐮 Oppty: unknown
Experiments: unknown
Last edited time: March 31, 2026 11:59 PM
👼: ✅
AI Thesis Eval (0-5): 4 - The thesis maps cleanly to Tradecore-supported markets because the venue set spans prediction, perps, and spot pairs where linked-state relationships exist. Honest sizing is still unavailable because Tradecore does not yet persist a stable historical graph-state replay surface.

## Summary

The lane memo argued that linked markets should be monitored as a graph, not as isolated pairwise spreads. In Tradecore terms, the spherical cow is a graph-aware repair monitor that watches which relationships break, which repair first, and whether the lagging edge remains executable long enough to matter.

This overlaps with Tradecore's lead-lag research, but it is broader than plain lead-lag. The hypothesis is not just "venue A moves before venue B." It is "a graph of related prices or implied states enters an inconsistent configuration, and some edges predictably lag because they sit behind slower liquidity, protection, or hedge states."

The correct first pass is therefore a graph-aware replay study, not an execution launch.

## "Spherical Cow" Opportunity

---

Spherical Cow data

Query 1: Funnel counts

Query 2: Where opportunities die (graph-construction stage)

Query 3: Where opportunities die (repair-event detection stage)

Query 4: Where opportunities die (execution gate)

Query 5: Edge distribution

Query 6: Fill performance

Query 7: Time-series funnel

---

## Spherical Cow Analysis — March 2026 (Tradecore-Supported Linked Markets)

*Methodology: constrained to supported venues only: Kalshi, Polymarket, Limitless, Hyperliquid, Coinbase, and Binance. The honest first pass requires a historical graph-state replay surface linking prices or implied states across related markets. Tradecore does not yet persist that surface in a research-ready form.*

### Recommendation

**Do not size this yet. First build one concrete graph family and replay its repair events.**

The first pass should not attempt a universal graph across all supported venues. It should start with one graph family:

- matched prediction venues pricing the same event
- perp / spot pairs where hedge links are clear
- a small linked set where graph-state definitions are explicit and replayable

### Detection Funnel

| Stage | n | Notes |
| --- | --- | --- |
| Candidate graph families | unknown | The venue set is known, but the graph definition must be chosen explicitly |
| Historical synchronized graph state | unknown | Tradecore supports venue ingestion, but not a persisted graph replay surface |
| Detected graph inconsistency events | unknown | Cannot be estimated honestly without the earlier stage |
| Events with lagging-edge identity | unknown | Requires graph-aware event labeling, not just pairwise spreads |
| Executable repair windows | unknown | Also unknown without matched graph history |

### Where the Opportunity Probably Lives

- Matched prediction markets across Kalshi, Polymarket, and Limitless where one venue or side of the graph repairs later than the others.
- Hyperliquid perp versus Coinbase / Binance spot relationships where hedge-linked state can temporarily disagree.
- Small linked market families where pairwise monitoring misses the fact that the lagging edge is determined by the wider graph configuration.

### What "Viable" Would Look Like

A viable version of this motif would show:

- better repair-time prediction from graph-aware features than from pairwise spread-only features
- a repeatable lagging-edge identity during graph inconsistency events
- executable convergence capture or reduced hedge slippage from monitoring the graph
- robustness across time instead of one narrow episode

### Why The Unknowns Stay Unknown

Tradecore has the venue support, but not yet the research substrate this motif needs:

- no canonical historical graph-state table
- no stable replay framework for inconsistency onset, partial repair, and full repair
- no honest funnel yet for how many graph-state breaks become executable repair trades

So the correct spherical-cow posture is: **credible graph-aware thesis, un-sized opportunity**.

### Smallest Honest First Pass

1. Pick one graph family with a clean state definition.
2. Persist synchronized prices or implied states for every edge in the graph.
3. Define graph inconsistency, partial repair, and full repair events.
4. Compare pairwise spread monitoring against a graph-aware repair timer.
5. Check whether graph-aware lag structure improves executable capture or hedge quality.

### Key Takeaways

1. This motif belongs in Tradecore because the supported venues span several plausible linked-market families.
2. The real edge is graph-aware repair timing, not just another lead-lag heuristic.
3. The blocker is the missing graph replay surface, not lack of a thesis.
4. APR, capacity, and opportunity count remain honestly unknown until that replay surface exists.

---
