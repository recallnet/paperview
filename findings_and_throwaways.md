# Findings and Throwaways

- accepted findings: `9`
- rejected interpretations: `2`
- near misses: `15`
- stranded q-fin failures: `3`

## Accepted Findings

### bridge

- none

### composition

- none

### stranded_qfin

- `stranded_qfin:2204.08581` | `STRANDED_QFIN_RESULT` | `high`
  title: Stranded resurfacing packet: On Parametric Optimal Execution and Machine Learning Surrogates
  result: Machine-learning surrogates can speed the search for near-optimal execution schedules under parametric impact models.
  clue: execution policy search with fast surrogates
  next step: Replicate the surrogate-assisted execution policy on newer fragmented limit-order-book data with realistic fees.
- `stranded_qfin:2106.00581` | `STRANDED_QFIN_RESULT` | `medium`
  title: Stranded resurfacing packet: $N$-player and Mean-field Games in Itô-diffusion Markets with Competitive or Homophilous Interaction
  result: The paper offers a concrete illiquidity-aware execution control that still looks testable on modern data.
  clue: adaptive execution with impact-aware control
  next step: Re-estimate the proposed impact-aware control on current intraday data and compare it to simpler adaptive execution baselines.

### transition_state

- `transition_state:near_transition_auction_queue:2101.03086` | `COMPOSITIONAL_CANDIDATE` | `medium`
  title: Transition-state packet: near auction handoff and queue value
  result: Queue value appears to change abruptly at the auction-to-continuous transition, suggesting a distinct post-uncrossing quoting regime.
  clue: auction handoff queue-value model
  next step: Measure whether queue priority gained immediately after auction uncrossing predicts short-horizon adverse selection.
- `transition_state:near_transition_auction_refill:1011.6402` | `TRANSLATION_CANDIDATE` | `medium`
  title: Transition-state packet: near auction handoff and refill resiliency
  result: Liquidity refill after auction uncrossing may lag the new price enough to create a brief execution edge.
  clue: auction handoff refill-lag monitor
  next step: Test refill-speed asymmetry immediately after auction uncrossing against naive post-auction mean-reversion signals.

### lifecycle

- `lifecycle:composition:lifecycle_professionalization__market_design_seams` | `TRANSLATION_CANDIDATE` | `medium`
  title: Composition packet: lifecycle_professionalization x market_design_seams
  result: Rules that look efficient in mature books may create larger gaps in earlier or less professionalized market regimes.
  clue: pre-professionalization market-structure seams
  next step: Compare early and mature market regimes to test whether the same venue rules produce different failure modes before and after professionalization.

### market_design

- `market_design:composition:market_design_seams__refill_lag_resiliency` | `TRANSLATION_CANDIDATE` | `medium`
  title: Composition packet: market_design_seams x refill_lag_resiliency
  result: Market-design choices appear to shape how quickly depth refills after shocks, making the same microstructure seam stronger in some rule sets than others.
  clue: market-structure-conditioned refill dislocations
  next step: Compare venue-rule changes against post-shock refill behavior to see whether specific matching and priority rules amplify resiliency gaps.

### participant_pathologies

- `participant_pathologies:composition:market_design_seams__participant_pathologies` | `TRANSLATION_CANDIDATE` | `medium`
  title: Composition packet: market_design_seams x participant_pathologies
  result: Participant pathologies such as toxic or manipulative flow may become more predictable when they interact with specific market-design rules.
  clue: rule-sensitive toxic-flow filters
  next step: Segment order flow by participant-toxicity proxies and test whether rule-sensitive adverse-selection patterns repeat around specific venue states.

### settlement_resolution

- `settlement_resolution:composition:amm_settlement_latency__settlement_resolution_seams` | `TRANSLATION_CANDIDATE` | `medium`
  title: Composition packet: amm_settlement_latency x settlement_resolution_seams
  result: Execution opportunities may persist when trades clear economically before they settle legally or operationally, creating exploitable timing gaps.
  clue: settlement-lag arbitrage and resolution-friction timing
  next step: Test whether settlement-cycle latency and margin timing create predictable basis or inventory pressure around execution and unwind windows.

### state_graph

- `state_graph:composition:market_design_seams__state_graph_inconsistencies` | `COMPOSITIONAL_CANDIDATE` | `medium`
  title: Composition packet: market_design_seams x state_graph_inconsistencies
  result: Cross-market inconsistencies may persist longer when the connected venues enforce different trading or protection rules.
  clue: venue-shaped delayed parity repair
  next step: Monitor related markets for temporary state disagreement and test whether venue-rule differences explain delayed convergence.

## Rejected Interpretations

### bridge

- none

### composition

- none

### stranded_qfin

- none

### unknown

- `market_design:composition:market_design_seams__refill_lag_local_shock` | reason `invalid_enum:classification:BAD_CLASS`
  title: no shortlist match
- `transition_state:near_transition_maker_queue:UNKNOWN` | reason `unknown_batch_item_id`
  title: no shortlist match

## Near Misses By Operator

### bridge

- `1609.04620` | score `2.683382` | rank `1`
  title: Price impact without order book: A study of the OTC credit index market
  operator clue: parity_propagation_delayed_repair x refill_lag_resiliency
- `1602.00731` | score `2.60741` | rank `1`
  title: Limit-order book resiliency after effective market orders: Spread, depth and intensity
  operator clue: market_design_seams x refill_lag_local_shock
- `1609.04620` | score `2.60502` | rank `1`
  title: Price impact without order book: A study of the OTC credit index market
  operator clue: market_design_seams x parity_propagation_delayed_repair

### composition

- `1609.04620` | score `3.492283` | rank `1`
  title: Price impact without order book: A study of the OTC credit index market
  operator clue: parity_propagation_delayed_repair x refill_lag_resiliency
- `1201.5448` | score `3.465987` | rank `1`
  title: Determinants of immediate price impacts at the trade level in an emerging order-driven market
  operator clue: refill_lag_local_shock x refill_lag_resiliency
- `1403.0842` | score `3.456498` | rank `2`
  title: The adaptive nature of liquidity taking in limit order books
  operator clue: refill_lag_local_shock x refill_lag_resiliency

### contrast

- `2205.14699` | score `3.889789` | rank `1`
  title: Managing Risk in DeFi Portfolios
  operator clue: near settlement, lexically far
- `2201.08875` | score `2.570519` | rank `1`
  title: Information-Based Trading
  operator clue: near auction design, lexically far
- `2012.13230` | score `2.55789` | rank `2`
  title: SoK: Lending Pools in Decentralized Finance
  operator clue: near settlement, lexically far

### negative_space

- `1405.5805` | score `2.930531` | rank `1`
  title: Micro and Macro Benefits of Random Investments in Financial Markets
  operator clue: Dead-end / theorem-only negative anchor
- `math/0703832` | score `2.86941` | rank `2`
  title: Queueing Theoretic Approaches to Financial Price Fluctuations
  operator clue: Dead-end / theorem-only negative anchor
- `0908.0949` | score `2.863749` | rank `3`
  title: A queueing theory description of fat-tailed price returns in imperfect financial markets
  operator clue: Dead-end / theorem-only negative anchor

### transition_state

- `2101.03086` | score `0.702172` | rank `1`
  title: Market Making with Stochastic Liquidity Demand: Simultaneous Order Arrival and Price Change Forecasts
  operator clue: near queue value and refill resiliency
- `2101.03086` | score `0.698541` | rank `1`
  title: Market Making with Stochastic Liquidity Demand: Simultaneous Order Arrival and Price Change Forecasts
  operator clue: near auction handoff and queue value
- `1011.6402` | score `0.680657` | rank `1`
  title: The Price Impact of Order Book Events
  operator clue: near parity repair and refill resiliency

## Stranded Q-Fin Failures

- `1712.10105` | resurfacing `0.380045` | reason `not_shortlisted_for_interpretation`
  title: Variance swaps under Lévy process with stochastic volatility and stochastic interest rate in incomplete markets
- `1903.06928` | resurfacing `0.379618` | reason `not_shortlisted_for_interpretation`
  title: Active and Passive Portfolio Management with Latent Factors
- `2005.04297` | resurfacing `0.378287` | reason `not_shortlisted_for_interpretation`
  title: Pricing Path-Dependent Derivatives under Multiscale Stochastic Volatility Models: a Malliavin Representation
