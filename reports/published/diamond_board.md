# Diamond Board

- entry count: `11`
- lane diversity: `6`

## Lane Coverage

- `market_design`: `2`
- `participant_pathologies`: `2`
- `settlement_resolution`: `1`
- `state_graph`: `2`
- `stranded_qfin`: `2`
- `transition_state`: `2`

## Board

### 1. Market Design packet: market_design_seams x parity_propagation

- lane family: `market_design`
- source surface: `early_market_failure_modes_ledger`
- publication item id: `market_design:composition:market_design_seams__parity_propagation`
- confidence: `medium`

Result: Market-design differences appear to change how quickly linked markets repair temporary inconsistencies.

Modern equivalent: venue-shaped delayed parity repair

First test: Compare venue rule differences against delayed cross-market convergence after local dislocations.

Gap to close: Need venue-specific rule metadata aligned to linked-market repair windows.

### 2. Participant Pathologies packet: How does the market react to your order flow?

- lane family: `participant_pathologies`
- source surface: `early_market_failure_modes_ledger`
- publication item id: `participant_pathologies:1104.0587`
- confidence: `medium`

Result: Participant pathologies look more repeatable when interpreted through venue-state and rule constraints rather than as generic bad behavior.

Modern equivalent: rule-sensitive toxic-flow filters

First test: Segment cancellation and sweep bursts by venue state to test whether toxic-flow episodes become more predictable under specific rule settings.

Gap to close: Need participant-toxicity proxies that survive without direct trader IDs.

### 3. Settlement Resolution packet: market_design_seams x settlement_resolution_seams

- lane family: `settlement_resolution`
- source surface: `early_market_failure_modes_ledger`
- publication item id: `settlement_resolution:composition:market_design_seams__settlement_resolution_seams`
- confidence: `medium`

Result: Settlement frictions and market rules together suggest a seam between economic execution and legal resolution.

Modern equivalent: rule-conditioned settlement lag arbitrage

First test: Test whether settlement timing and venue-rule mismatches create repeatable basis or unwind windows around resolution events.

Gap to close: Need synchronized execution, collateral, and settlement-state data rather than trade prints alone.

### 4. State Graph packet: Foreign exchange markets: price response and spread impact

- lane family: `state_graph`
- source surface: `early_market_failure_modes_ledger`
- publication item id: `state_graph:2104.09309`
- confidence: `medium`

Result: The candidate reads like a repair-timing workflow across temporarily inconsistent market states rather than a standalone arbitrage rule.

Modern equivalent: state-graph inconsistency monitor

First test: Monitor linked markets for transient state disagreement and test whether delayed repair predicts execution quality or hedging slippage.

Gap to close: Need a consistent state graph across the connected instruments, not just prices at one timestamp.

### 5. 2106.00581

- lane family: `stranded_qfin`
- source surface: `stranded_result_ledger`
- publication item id: `stranded_qfin:2106.00581`
- confidence: `medium`

Result: The paper offers a concrete illiquidity-aware control law that still looks testable with modern market data.

Modern equivalent: adaptive execution with impact-aware control

First test: Re-estimate the illiquidity-aware control on current intraday data and compare it against simpler adaptive execution baselines.

Gap to close: Need proof that the control survives modern queue dynamics and hidden-liquidity behavior.

### 6. near parity repair and refill resiliency

- lane family: `transition_state`
- source surface: `transition_state_ledger`
- publication item id: `transition_state:near_transition_parity_repair:1609.04620`
- confidence: `medium`

Result: The edge appears to live at the boundary where linked markets begin repairing an inconsistency, not in generic spread mean reversion.

Modern equivalent: parity-repair transition monitor

First test: Measure whether execution quality changes specifically at parity-repair state boundaries rather than across steady-state trading intervals.

Gap to close: Need exact event definitions for the transition boundary and post-transition repair window.

### 7. Market Design packet: market_design_seams x parity_propagation

- lane family: `market_design`
- source surface: `unrealized_ideas_index`
- publication item id: `market_design:composition:market_design_seams__parity_propagation`
- confidence: `medium`

Result: Market-design differences appear to change how quickly linked markets repair temporary inconsistencies.

Modern equivalent: venue-shaped delayed parity repair

First test: Compare venue rule differences against delayed cross-market convergence after local dislocations.

Gap to close: Need venue-specific rule metadata aligned to linked-market repair windows.

### 8. Participant Pathologies packet: How does the market react to your order flow?

- lane family: `participant_pathologies`
- source surface: `unrealized_ideas_index`
- publication item id: `participant_pathologies:1104.0587`
- confidence: `medium`

Result: Participant pathologies look more repeatable when interpreted through venue-state and rule constraints rather than as generic bad behavior.

Modern equivalent: rule-sensitive toxic-flow filters

First test: Segment cancellation and sweep bursts by venue state to test whether toxic-flow episodes become more predictable under specific rule settings.

Gap to close: Need participant-toxicity proxies that survive without direct trader IDs.

### 9. State Graph packet: Foreign exchange markets: price response and spread impact

- lane family: `state_graph`
- source surface: `unrealized_ideas_index`
- publication item id: `state_graph:2104.09309`
- confidence: `medium`

Result: The candidate reads like a repair-timing workflow across temporarily inconsistent market states rather than a standalone arbitrage rule.

Modern equivalent: state-graph inconsistency monitor

First test: Monitor linked markets for transient state disagreement and test whether delayed repair predicts execution quality or hedging slippage.

Gap to close: Need a consistent state graph across the connected instruments, not just prices at one timestamp.

### 10. 2204.08581

- lane family: `stranded_qfin`
- source surface: `stranded_result_ledger`
- publication item id: `stranded_qfin:2204.08581`
- confidence: `high`

Result: Machine-learning surrogates can accelerate the search for useful execution controls under impact-aware models.

Modern equivalent: execution policy search with fast surrogates

First test: Replay the surrogate-assisted execution policy on recent fragmented book data with realistic fee and queue assumptions.

Gap to close: Need evidence that the surrogate remains stable under fragmentation and hidden-liquidity effects.

### 11. near queue value and refill resiliency

- lane family: `transition_state`
- source surface: `transition_state_ledger`
- publication item id: `transition_state:near_transition_queue_refill:1602.00731`
- confidence: `medium`

Result: Queue value appears to change at the refill boundary, creating a distinct post-shock quoting regime.

Modern equivalent: queue-value x refill-lag regime switch

First test: Compare passive fill quality immediately after a refill transition against a naive always-post baseline.

Gap to close: Need venue-specific queue position and refill state measurements to separate true recovery from stale displayed depth.
