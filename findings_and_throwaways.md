# Findings and Throwaways

- accepted findings: `8`
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
  title: Stranded q-fin packet: On Parametric Optimal Execution and Machine Learning Surrogates
  result: Machine-learning surrogates can accelerate the search for useful execution controls under impact-aware models.
  clue: execution policy search with fast surrogates
  next step: Replay the surrogate-assisted execution policy on recent fragmented book data with realistic fee and queue assumptions.
- `stranded_qfin:2106.00581` | `STRANDED_QFIN_RESULT` | `medium`
  title: Stranded q-fin packet: $N$-player and Mean-field Games in Itô-diffusion Markets with Competitive or Homophilous Interaction
  result: The paper offers a concrete illiquidity-aware control law that still looks testable with modern market data.
  clue: adaptive execution with impact-aware control
  next step: Re-estimate the illiquidity-aware control on current intraday data and compare it against simpler adaptive execution baselines.

### transition_state

- `transition_state:near_transition_parity_repair:1609.04620` | `TRANSITION_SEAM` | `medium`
  title: Transition-state packet: near parity repair and refill resiliency
  result: The edge appears to live at the boundary where linked markets begin repairing an inconsistency, not in generic spread mean reversion.
  clue: parity-repair transition monitor
  next step: Measure whether execution quality changes specifically at parity-repair state boundaries rather than across steady-state trading intervals.
- `transition_state:near_transition_queue_refill:1602.00731` | `TRANSITION_SEAM` | `medium`
  title: Transition-state packet: near queue value and refill resiliency
  result: Queue value appears to change at the refill boundary, creating a distinct post-shock quoting regime.
  clue: queue-value x refill-lag regime switch
  next step: Compare passive fill quality immediately after a refill transition against a naive always-post baseline.

### market_design

- `market_design:composition:market_design_seams__parity_propagation` | `TRANSLATION_CANDIDATE` | `medium`
  title: Market Design packet: market_design_seams x parity_propagation
  result: Market-design differences appear to change how quickly linked markets repair temporary inconsistencies.
  clue: venue-shaped delayed parity repair
  next step: Compare venue rule differences against delayed cross-market convergence after local dislocations.

### settlement_resolution

- `settlement_resolution:composition:market_design_seams__settlement_resolution_seams` | `COMPOSITIONAL_CANDIDATE` | `medium`
  title: Settlement Resolution packet: market_design_seams x settlement_resolution_seams
  result: Settlement frictions and market rules together suggest a seam between economic execution and legal resolution.
  clue: rule-conditioned settlement lag arbitrage
  next step: Test whether settlement timing and venue-rule mismatches create repeatable basis or unwind windows around resolution events.

### participant_pathologies

- `participant_pathologies:1104.0587` | `TRANSLATION_CANDIDATE` | `medium`
  title: Participant Pathologies packet: How does the market react to your order flow?
  result: Participant pathologies look more repeatable when interpreted through venue-state and rule constraints rather than as generic bad behavior.
  clue: rule-sensitive toxic-flow filters
  next step: Segment cancellation and sweep bursts by venue state to test whether toxic-flow episodes become more predictable under specific rule settings.

### state_graph

- `state_graph:2104.09309` | `COMPOSITIONAL_CANDIDATE` | `medium`
  title: State Graph packet: Foreign exchange markets: price response and spread impact
  result: The candidate reads like a repair-timing workflow across temporarily inconsistent market states rather than a standalone arbitrage rule.
  clue: state-graph inconsistency monitor
  next step: Monitor linked markets for transient state disagreement and test whether delayed repair predicts execution quality or hedging slippage.

## Rejected Interpretations

### bridge

- none

### composition

- none

### stranded_qfin

- none

### transition_state

- none

### market_design

- none

### settlement_resolution

- none

### participant_pathologies

- none

### state_graph

- none

### unknown

- `market_design:composition:market_design_seams__refill_lag_local_shock` | reason `invalid_enum:classification:BAD_CLASS`
  title: no shortlist match
- `transition_state:near_transition_maker_queue:UNKNOWN` | reason `unknown_batch_item_id`
  title: no shortlist match

## Near Misses By Operator

### bridge

- `2009.02808` | score `2.441005` | rank `1`
  title: Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants
  operator clue: queue_value_passive_quoting x refill_lag_local_shock
- `cond-mat/0210475` | score `2.354075` | rank `1`
  title: Statistical theory of the continuous double auction
  operator clue: auction_parimutuel_design x refill_lag_local_shock
- `1005.0182` | score `2.34996` | rank `2`
  title: A Multi Agent Model for the Limit Order Book Dynamics
  operator clue: queue_value_passive_quoting x refill_lag_local_shock

### composition

- `2009.02808` | score `3.202651` | rank `1`
  title: Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants
  operator clue: queue_value_passive_quoting x refill_lag_local_shock
- `1207.2946` | score `3.156657` | rank `2`
  title: Microscopic understanding of heavy-tailed return distributions in an agent-based model
  operator clue: queue_value_passive_quoting x refill_lag_local_shock
- `1005.0182` | score `3.135477` | rank `3`
  title: A Multi Agent Model for the Limit Order Book Dynamics
  operator clue: queue_value_passive_quoting x refill_lag_local_shock

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
