# Research Output

## Executive Summary

The strongest cross-domain clue is `bridge:queue_value_passive_quoting__refill_lag_local_shock`: Passive quote value after a shock appears to depend on both queue priority and liquidity refill lag rather than on spread alone.
The stranded q-fin resurfacing pass produced concrete execution-style results, led by `stranded_qfin:2106.00581` and `adaptive execution with impact-aware control`.
The clearest microstructure seam is `near auction handoff and queue value`: Queue value appears to change abruptly at the auction-to-continuous transition, suggesting a distinct post-uncrossing quoting regime.
The remaining throwaways still matter because they separate explicit rejections from high-value near misses and stranded failures that deserve another research pass.

## Unrealized Cross-Domain Ideas

### 1. Bridge packet: queue_value_passive_quoting x refill_lag_local_shock

- publication id: `bridge:queue_value_passive_quoting__refill_lag_local_shock`
- classification: `COMPOSITIONAL_CANDIDATE`
- confidence: `medium`
- result: Passive quote value after a shock appears to depend on both queue priority and liquidity refill lag rather than on spread alone.
- modern equivalent: post-shock passive quoting in electronic books
- first test: Measure queue-position edge after volatility shocks with refill-time controls on recent LOB data.
- why unrealized: The literature isolates queue value and resiliency separately and stops short of an execution rule that combines them.
- holdout echoes:
  - `1902.10743` | From Glosten-Milgrom to the whole limit order book and applications to financial regulation | echo `0.827148`
  - `2408.03181` | Correlation emergence in two coupled simulated limit order books | echo `0.78294`
  - `2406.04969` | An Algebraic Framework for the Modeling of Limit Order Books | echo `0.766262`

## Stranded Q-Fin Results

### 1. 2106.00581

- publication id: `stranded_qfin:2106.00581`
- confidence: `medium`
- priority tier: `p2`
- result: The paper offers a concrete illiquidity-aware execution control that still looks testable on modern data.
- why stranded: It reads like mathematical finance rather than a practitioner-ready execution template, so the result never surfaced as a live strategy clue.
- instrument assumed: intraday optimal execution under temporary impact
- modern equivalent: adaptive execution with impact-aware control
- first test: Re-estimate the proposed impact-aware control on current intraday data and compare it to simpler adaptive execution baselines.
- gap to close: Need evidence that the control law survives modern queue dynamics and hidden-liquidity behavior.

### 2. 2204.08581

- publication id: `stranded_qfin:2204.08581`
- confidence: `high`
- priority tier: `p2`
- result: Machine-learning surrogates can speed the search for near-optimal execution schedules under parametric impact models.
- why stranded: The result is practical but remained stranded inside execution-model calibration language instead of being promoted as a deployable trading workflow.
- instrument assumed: algorithmic execution in liquid futures or equities
- modern equivalent: execution policy search with fast surrogates
- first test: Replicate the surrogate-assisted execution policy on newer fragmented limit-order-book data with realistic fees.
- gap to close: Need to show that the surrogate remains stable under venue fragmentation and regime shifts.

## Transition-State Microstructure Seams

### 1. near auction handoff and queue value

- publication id: `transition_state:near_transition_auction_queue:2101.03086`
- representative paper: `2101.03086`
- confidence: `medium`
- priority tier: `p1`
- result: Queue value appears to change abruptly at the auction-to-continuous transition, suggesting a distinct post-uncrossing quoting regime.
- why unrealized: Auction studies and queue-value studies are adjacent but stop short of a combined transition-state hypothesis.
- instrument assumed: opening or closing auction transition in lit books
- modern equivalent: auction handoff queue-value model
- first test: Measure whether queue priority gained immediately after auction uncrossing predicts short-horizon adverse selection.
- gap to close: Need a venue-by-venue definition of the auction-to-book state boundary.

### 2. near auction handoff and refill resiliency

- publication id: `transition_state:near_transition_auction_refill:1011.6402`
- representative paper: `1011.6402`
- confidence: `medium`
- priority tier: `p1`
- result: Liquidity refill after auction uncrossing may lag the new price enough to create a brief execution edge.
- why unrealized: The literature frames the phenomenon as market design and resiliency, not as a trading or quoting signal.
- instrument assumed: post-auction spread and depth normalization
- modern equivalent: auction handoff refill-lag monitor
- first test: Test refill-speed asymmetry immediately after auction uncrossing against naive post-auction mean-reversion signals.
- gap to close: Need microsecond-resolution venue data to separate refill from directional continuation.

## Near-Misses and Throwaways

### Rejected Interpretations

- `transition_state:near_transition_parity_repair:2406.04969` | reason `unknown_batch_item_id`
  title: no matched packet
- `transition_state:near_transition_maker_queue:UNKNOWN` | reason `unknown_batch_item_id`
  title: no matched packet
- `bridge:parity_propagation__queue_value_passive_quoting` | reason `invalid_enum:classification:BAD_CLASS`
  title: no matched packet

### Operator Near-Misses

- `2009.02808` | `bridge` | score `2.441005`
  title: Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants
  clue: queue_value_passive_quoting x refill_lag_local_shock
- `cond-mat/0210475` | `bridge` | score `2.354075`
  title: Statistical theory of the continuous double auction
  clue: auction_parimutuel_design x refill_lag_local_shock
- `1005.0182` | `bridge` | score `2.34996`
  title: A Multi Agent Model for the Limit Order Book Dynamics
  clue: queue_value_passive_quoting x refill_lag_local_shock
- `2009.02808` | `composition` | score `3.202651`
  title: Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants
  clue: queue_value_passive_quoting x refill_lag_local_shock
- `1207.2946` | `composition` | score `3.156657`
  title: Microscopic understanding of heavy-tailed return distributions in an agent-based model
  clue: queue_value_passive_quoting x refill_lag_local_shock
- `1005.0182` | `composition` | score `3.135477`
  title: A Multi Agent Model for the Limit Order Book Dynamics
  clue: queue_value_passive_quoting x refill_lag_local_shock
- `2205.14699` | `contrast` | score `3.889789`
  title: Managing Risk in DeFi Portfolios
  clue: near settlement, lexically far
- `2201.08875` | `contrast` | score `2.570519`
  title: Information-Based Trading
  clue: near auction design, lexically far
- `2012.13230` | `contrast` | score `2.55789`
  title: SoK: Lending Pools in Decentralized Finance
  clue: near settlement, lexically far
- `1405.5805` | `negative_space` | score `2.930531`
  title: Micro and Macro Benefits of Random Investments in Financial Markets
  clue: Dead-end / theorem-only negative anchor
- `math/0703832` | `negative_space` | score `2.86941`
  title: Queueing Theoretic Approaches to Financial Price Fluctuations
  clue: Dead-end / theorem-only negative anchor
- `0908.0949` | `negative_space` | score `2.863749`
  title: A queueing theory description of fat-tailed price returns in imperfect financial markets
  clue: Dead-end / theorem-only negative anchor
- `2101.03086` | `transition_state` | score `0.702172`
  title: Market Making with Stochastic Liquidity Demand: Simultaneous Order Arrival and Price Change Forecasts
  clue: near queue value and refill resiliency
- `2101.03086` | `transition_state` | score `0.698541`
  title: Market Making with Stochastic Liquidity Demand: Simultaneous Order Arrival and Price Change Forecasts
  clue: near auction handoff and queue value
- `1011.6402` | `transition_state` | score `0.680657`
  title: The Price Impact of Order Book Events
  clue: near parity repair and refill resiliency

### Stranded Q-Fin Failures

- `1712.10105` | reason `interpretation_classification:NO_TRANSLATION`
  title: Variance swaps under Lévy process with stochastic volatility and stochastic interest rate in incomplete markets
- `1903.06928` | reason `not_shortlisted_for_interpretation`
  title: Active and Passive Portfolio Management with Latent Factors
- `2005.04297` | reason `not_shortlisted_for_interpretation`
  title: Pricing Path-Dependent Derivatives under Multiscale Stochastic Volatility Models: a Malliavin Representation

## What to Investigate Next

- Validate `bridge:queue_value_passive_quoting__refill_lag_local_shock` on recent order-book data: Measure queue-position edge after volatility shocks with refill-time controls on recent LOB data.
- Treat `near auction handoff and queue value` as the top transition-state seam and test: Measure whether queue priority gained immediately after auction uncrossing predicts short-horizon adverse selection.
- Resurface `2106.00581` into a live execution memo: Re-estimate the proposed impact-aware control on current intraday data and compare it to simpler adaptive execution baselines.
- Review stranded failure `1712.10105` to decide whether it needs a new interpretation pass or explicit rejection.
