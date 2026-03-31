# State-Graph Repair Timing Monitor

Categories: Prediction Markets, Perpetuals, Spot Crypto
Strategy Theme: Graph-Aware Relative Value
Venues: Kalshi, Polymarket, Limitless, Hyperliquid, Coinbase, Binance
Edge Description: Linked markets should be treated as a state graph whose inconsistencies repair on different clocks. The edge is not a single spread or pair trade; it is the timing pattern of which related prices, implied states, or hedge links lag and which repair first.
Null Hypothesis: Graph-aware repair timing across supported venues does not add enough predictive value beyond ordinary pairwise spreads or lead-lag effects to generate returns materially above fees and slippage.
🐮 APR: 10%
🐮 Capacity ($M/Year): $0.002
🐮 Oppty: 5-15 tradeable graph-repair windows/day

## Summary

The lane memo argued that linked markets should be monitored as a graph, not as isolated pairwise spreads. In Tradecore terms, the spherical cow is a graph-aware repair monitor that watches which relationships break, which repair first, and whether the lagging edge remains executable long enough to matter.

This overlaps with Tradecore's lead-lag research, but it is broader than plain lead-lag. The hypothesis is not just "venue A moves before venue B." It is "a graph of related prices or implied states enters an inconsistent configuration, and some edges predictably lag because they sit behind slower liquidity, protection, or hedge states."

The correct first pass is therefore a graph-aware replay study, not an execution launch, and the figures below should be read as conservative planning estimates rather than measured truth.

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

*Methodology: constrained to supported venues only: Kalshi, Polymarket, Limitless, Hyperliquid, Coinbase, and Binance. The honest first pass requires a historical graph-state replay surface linking prices or implied states across related markets. Tradecore does not yet persist that surface in a research-ready form, so the figures below are explicit planning estimates derived from Tradecore's existing cross-venue fragmentation, triangular-parity, and lead-lag priors, with a haircut for the extra complexity of graph-aware event labeling.*

### Recommendation

**Treat this as a medium-frequency graph-aware timing seam worth replaying before any execution build.**

The first pass should not attempt a universal graph across all supported venues. It should start with one graph family:

- matched prediction venues pricing the same event
- perp / spot pairs where hedge links are clear
- a small linked set where graph-state definitions are explicit and replayable

### Detection Funnel

| Stage | n | Notes |
| --- | --- | --- |
| Candidate graph families | ~3 realistic families | matched prediction venues, perp-spot hedge links, and small parity baskets are the practical first-pass families |
| Historical synchronized graph state | partial only | venue support exists, but not as a persisted replay surface |
| Detected graph inconsistency events | estimated 10-30/day | conservative subset of broader spread and parity disruptions |
| Events with lagging-edge identity | estimated 5-15/day | assumes many raw graph breaks collapse to obvious pairwise moves and add no extra graph value |
| Executable repair windows | estimated 5-15/day | same practical range after a haircut for labeling complexity and overlap with simpler motifs |

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

### Estimated Economics

These are spherical-cow estimates, not measured production outputs.

- Estimated annual revenue capacity: roughly `$0.001M-$0.003M/year`
- Estimated center-case capacity used here: `$0.002M/year`
- Estimated tradeable graph-repair windows: `5-15/day`
- Estimated center-case APR used here: `10%`

Reasoning:

- Tradecore already has a same-market fragmentation prior with roughly `~100` matched pairs and a parity motif that is small but real, so the graph-aware universe is not hypothetical.
- But this motif is stricter than plain spread capture because it requires identifying which edge in the graph lags and proving that the graph representation adds signal beyond pairwise monitoring.
- The estimate therefore sits below the market-design delayed-parity memo on clarity, but above the settlement seam on expected event count because the underlying graph breaks should occur more often than true resolution-friction windows.
- A `10%` APR and `$0.002M/year` center-case is a conservative planning prior for a monitor that may improve capture on existing relative-value opportunities rather than create a wholly separate high-capacity strategy.

### Why These Are Estimates

Tradecore has the venue support, but not yet the research substrate this motif needs:

- no canonical historical graph-state table
- no stable replay framework for inconsistency onset, partial repair, and full repair
- no honest replay yet for how many graph-state breaks become executable repair trades

So the correct spherical-cow posture is: **credible graph-aware thesis, roughly sized opportunity with low confidence until replay data exists**.

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
4. APR, capacity, and opportunity count are now explicit estimates, but they should still be treated as planning priors until that replay surface exists.

---
