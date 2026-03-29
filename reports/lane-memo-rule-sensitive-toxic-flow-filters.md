# Rule-Sensitive Toxic-Flow Filters

## Thesis

Toxic or manipulative flow should become more predictable when venue rules expose or amplify it, so the right filter is not generic toxicity detection but a venue-state model that conditions flow signatures on priority, latency, and protection rules.

## Why This Lead Exists

The accepted participant-pathology publication row says participant pathologies become more repeatable when interpreted through venue-state and rule constraints. The bridge-zone evidence sharpens that into an executable question: which rule settings make informed, predatory, or manipulative behavior visible enough to trade against?

## Supporting Papers

- `1104.0587` (How does the market react to your order flow?): anchors the core question of how markets react to observable order flow rather than to abstract participant labels.
- `0908.0202` (Market impact and trading profile of large trading orders in stock markets): connects large-order trading profiles to persistent impact signatures that can be filtered rather than merely described.
- `1903.12458` (Market Manipulation as a Security Problem): frames manipulation as a security problem, which makes rule sensitivity part of the threat surface instead of background context.
- `1311.4160` (Simulating the Synchronizing Behavior of High-Frequency Trading in Multiple Markets): shows that synchronized high-frequency behavior across venues can emerge endogenously when the market design permits it.
- `2006.08682` (The Importance of Low Latency to Order Book Imbalance Trading Strategies) and `2009.02808` (Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants): provide concrete low-latency and heterogeneous-information surfaces where venue rules likely change how toxic flow appears in the book.
- `2003.04425` (Informed trading, limit order book and implementation shortfall: equilibrium and asymptotics): ties informed trading, the order book, and implementation shortfall together, which is exactly the seam the memo tries to operationalize.

## Hypothesis

Cancellation bursts, sweep patterns, or imbalance shocks should have higher predictive value for adverse selection when they occur under specific venue states such as wide-tick regimes, low-latency priority races, auction handoff windows, or weak protection rules. The same raw flow pattern should be less informative outside those states.

## Data

- Event-level order-book data with cancellations, modifications, and aggressive trades.
- Venue-state labels: tick regime, priority rule, auction/protection state, latency tier if available, and any visible queue-priority constraints.
- A toxicity proxy such as short-horizon adverse selection, markout, or sweep-induced impact.
- At least three months of data for one venue family so venue-state strata have enough coverage.

## Baseline

An unconditional toxic-flow classifier that uses order-flow imbalance, cancellation rate, and sweep count without conditioning on venue state or rule configuration.

## Seam-Aware Program

Estimate toxicity only inside explicit rule states. The first pass should segment events by venue state, then ask whether cancellation spikes, sweep bursts, or imbalance shocks predict adverse selection materially better in some rule regimes than in others.

## First Test

Segment cancellation and sweep bursts by venue state to test whether toxic-flow episodes become more predictable under specific rule settings. Compare predictive lift for short-horizon markouts between a state-aware filter and the unconditional baseline.

## Metric

Primary metric: incremental predictive value for short-horizon adverse selection or markout from adding venue-state interactions. Secondary metrics: false-positive rate on benign flow, fill-quality improvement after filtering, and stability across time-of-day and volatility regimes.

## Fail-Fast

- If state conditioning adds no predictive lift beyond plain toxicity proxies, this is not a rule-sensitive seam.
- If the result depends on participant IDs that are not observable in production, the memo is not deployable.
- If the filter only works in one narrow venue state with negligible trade count, the lead is too brittle to matter.

## Stop / Go

Go if at least one venue-state interaction materially improves toxic-flow prediction and translates into better passive or reactive execution quality. Stop if venue-state features behave like redundant descriptions of spread and volatility rather than true amplifiers of toxicity.

## Gap To Close

The remaining gap is a production-grade toxicity proxy that survives without direct trader identifiers. The memo is strong only if venue state can replace missing participant labels rather than merely complement them in offline analysis.

