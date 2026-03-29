# State-Graph Repair Timing Monitor

## Thesis

Linked markets should be monitored as a state graph whose inconsistent edges repair on different clocks, so the tradeable signal is not the raw spread but the timing pattern of which state relationships lag and which ones heal first.

## Why This Lead Exists

The accepted state-graph publication row already says the candidate is a repair-timing workflow across temporarily inconsistent market states. The related parity-repair evidence shows that some of these edges become executable only around the repair boundary, which means the operational task is to monitor graph state transitions rather than to chase isolated price gaps.

## Supporting Papers

- `2104.09309` (Foreign exchange markets: price response and spread impact): is the accepted anchor because it frames price response and spread impact in a way that naturally extends to linked-state repair monitoring.
- `1111.7103` (High Frequency Lead/lag Relationships - Empirical facts): provides direct high-frequency lead-lag evidence that some linked relationships consistently move before others.
- `2010.15105` (Price response functions and spread impact in correlated financial markets): turns correlated-market response into an explicit spread-impact problem rather than a single-instrument signal.
- `2004.12011` (Trading Foreign Exchange Triplets): grounds the graph view with a concrete multi-leg consistency problem in FX triplets.
- `1609.04620` (Price impact without order book: A study of the OTC credit index market) and `1811.08038` (Arbitrage Opportunities in CDS Term Structure: Theory and Implications for OTC Derivatives): show that graph repair can be slowed or distorted when market structure or post-trade state interferes with immediate convergence.

## Hypothesis

When a linked market graph enters an inconsistent state, the order and speed with which edges repair should predict where executable hedging slippage or convergence capture is available. Some edges should systematically lag because they sit behind slower liquidity, protection, or settlement states.

## Data

- Synchronized prices or quotes for all instruments in one linked graph, such as FX triangles, ETF-basket relationships, or cash-futures pairs.
- A reproducible graph-state definition for each edge, including parity, basis, or implied-price relationships.
- Event timestamps for graph inconsistency onset, partial repair, and full repair.
- At least three months of data so lag structure can be estimated across many repair events.

## Baseline

A pairwise spread monitor that treats each inconsistency independently and ignores the order in which the wider graph repairs.

## Seam-Aware Program

Construct a live state graph and classify each event by which edges are broken, which edges repair first, and how long each remaining inconsistency survives. The first model should test whether lagging-edge identity improves prediction of executable repair timing beyond pairwise spread size alone.

## First Test

Monitor linked markets for transient state disagreement and test whether delayed repair predicts execution quality or hedging slippage. Start with one graph, detect inconsistency events, and compare a graph-aware repair timer against a pairwise spread baseline.

## Metric

Primary metric: improvement in repair-time prediction from graph-aware edge-order features over pairwise spread-only features. Secondary metrics: executable convergence capture, hedge slippage during the lag window, and false alarms where pairwise gaps never become tradeable repair events.

## Fail-Fast

- If graph-aware features add no signal beyond pairwise spread size, this is not a state-graph seam.
- If synchronization errors across feeds create fake graph lags, the monitor is just measuring data latency.
- If the lagging edge is statistically stable but not executable because liquidity vanishes before repair, the lead is descriptive rather than practical.

## Stop / Go

Go if graph-aware lag structure materially improves repair-time prediction and points to better executable capture or lower hedging slippage than pairwise spread monitoring. Stop if the graph collapses to independent pairwise gaps once feed alignment and liquidity controls are applied.

## Gap To Close

The remaining gap is a robust event definition for graph inconsistency and repair. Without a stable graph-state ontology, the monitor will drift back into ad hoc spread watching.

