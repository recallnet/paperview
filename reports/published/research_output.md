# Research Memo

The broadened run suggests exploitable edge is not confined to mature electronic-book transition states: the strongest surviving ideas cluster where market design, settlement timing, participant pathology, state-graph inconsistency, and market maturation interact with execution microstructure.

## Broadest Surviving Leads

### 1. Composition packet: market_design_seams x refill_lag_resiliency

Lane: market design.
What it is: Market-design choices appear to shape how quickly depth refills after shocks, making the same microstructure seam stronger in some rule sets than others.
Why it survived: The literature treats market design and resiliency as separate topics instead of framing rule-induced refill lag as an execution seam.
First test: Compare venue-rule changes against post-shock refill behavior to see whether specific matching and priority rules amplify resiliency gaps.
Modern equivalent: market-structure-conditioned refill dislocations

### 2. Composition packet: amm_settlement_latency x settlement_resolution_seams

Lane: settlement resolution.
What it is: Execution opportunities may persist when trades clear economically before they settle legally or operationally, creating exploitable timing gaps.
Why it survived: The underlying papers frame the problem as settlement architecture or AMM latency rather than as a tradable seam between execution and final resolution.
First test: Test whether settlement-cycle latency and margin timing create predictable basis or inventory pressure around execution and unwind windows.
Modern equivalent: settlement-lag arbitrage and resolution-friction timing

### 3. Composition packet: lifecycle_professionalization x market_design_seams

Lane: lifecycle.
What it is: Rules that look efficient in mature books may create larger gaps in earlier or less professionalized market regimes.
Why it survived: The maturation literature describes changing market quality but rarely turns that into a search program for early-market executable seams.
First test: Compare early and mature market regimes to test whether the same venue rules produce different failure modes before and after professionalization.
Modern equivalent: pre-professionalization market-structure seams

### 4. Composition packet: market_design_seams x participant_pathologies

Lane: participant pathologies.
What it is: Participant pathologies such as toxic or manipulative flow may become more predictable when they interact with specific market-design rules.
Why it survived: The source literature studies bad actors and venue rules separately, leaving the repeated rule-by-participant seam implicit.
First test: Segment order flow by participant-toxicity proxies and test whether rule-sensitive adverse-selection patterns repeat around specific venue states.
Modern equivalent: rule-sensitive toxic-flow filters

### 5. Composition packet: market_design_seams x state_graph_inconsistencies

Lane: state graph.
What it is: Cross-market inconsistencies may persist longer when the connected venues enforce different trading or protection rules.
Why it survived: State-graph inconsistency papers and market-design papers have not been combined into a concrete convergence-timing workflow.
First test: Monitor related markets for temporary state disagreement and test whether venue-rule differences explain delayed convergence.
Modern equivalent: venue-shaped delayed parity repair

## Lane Coverage

The broadened discovery set now has surviving accepted interpretations in all five new early-market lanes, plus the existing stranded-q-fin and transition-state paths.

- market design: Market-design choices appear to shape how quickly depth refills after shocks, making the same microstructure seam stronger in some rule sets than others.
- settlement resolution: Execution opportunities may persist when trades clear economically before they settle legally or operationally, creating exploitable timing gaps.
- participant pathologies: Participant pathologies such as toxic or manipulative flow may become more predictable when they interact with specific market-design rules.
- state graph: Cross-market inconsistencies may persist longer when the connected venues enforce different trading or protection rules.
- lifecycle: Rules that look efficient in mature books may create larger gaps in earlier or less professionalized market regimes.
- stranded qfin: Machine-learning surrogates can speed the search for near-optimal execution schedules under parametric impact models.
- transition state: Queue value appears to change abruptly at the auction-to-continuous transition, suggesting a distinct post-uncrossing quoting regime.

## The Stranded Results That Came Back

### 2106.00581 — $N$-player and Mean-field Games in Itô-diffusion Markets with Competitive or Homophilous Interaction (2021-06-14)

What it is in plain language: The paper offers a concrete illiquidity-aware execution control that still looks testable on modern data.
Why it matters now: It reads like mathematical finance rather than a practitioner-ready execution template, so the result never surfaced as a live strategy clue.
Modern equivalent: adaptive execution with impact-aware control
First test: Re-estimate the proposed impact-aware control on current intraday data and compare it to simpler adaptive execution baselines.
Gap remaining: Need evidence that the control law survives modern queue dynamics and hidden-liquidity behavior.

### 2204.08581 — On Parametric Optimal Execution and Machine Learning Surrogates (2023-10-29)

What it is in plain language: Machine-learning surrogates can speed the search for near-optimal execution schedules under parametric impact models.
Why it matters now: The result is practical but remained stranded inside execution-model calibration language instead of being promoted as a deployable trading workflow.
Modern equivalent: execution policy search with fast surrogates
First test: Replicate the surrogate-assisted execution policy on newer fragmented limit-order-book data with realistic fees.
Gap remaining: Need to show that the surrogate remains stable under venue fragmentation and regime shifts.

## Transition-State Seams Still Matter

The broadened run no longer treats transition-state microstructure as the only center of gravity, but the venue-level auction and queue seams remain the clearest microstructure benchmark.

- near auction handoff and queue value: Queue value appears to change abruptly at the auction-to-continuous transition, suggesting a distinct post-uncrossing quoting regime. First test: Measure whether queue priority gained immediately after auction uncrossing predicts short-horizon adverse selection.
- near auction handoff and refill resiliency: Liquidity refill after auction uncrossing may lag the new price enough to create a brief execution edge. First test: Test refill-speed asymmetry immediately after auction uncrossing against naive post-auction mean-reversion signals.

## The Conversion Funnel

The search started with 17,323 scored discovery papers, narrowed to 24 shortlist items, then to 9 accepted broadened interpretations, and finally to 5 unrealized cross-domain entries, 2 stranded q-fin results, and 2 transition-state entries.
What this means: discovery is now broader than the original microstructure loop, but publication is still selective. The system can find multi-lane seams; the remaining bottleneck is converting those seams into dense interpretation evidence and durable publication rows.

## What To Do Next

Operationalize the broadened publication set in three tracks.
1. Build lane-specific research programs for the surviving market-design, settlement-resolution, participant-pathology, state-graph, and lifecycle leads, using the unrealized index rows as the canonical queue of next experiments.
2. Keep the stranded q-fin results on a separate execution track, because those papers are already close to deployable execution research rather than broad discovery hypotheses.
3. Use the transition-state ledger as the venue-microstructure benchmark so the broader lanes can be compared against the older queue/refill seam instead of replacing it blindly.

## Papers Worth a Second Look

- `1609.04620` (Price impact without order book: A study of the OTC credit index market) is worth another pass because it keeps appearing near the parity_propagation_delayed_repair x refill_lag_resiliency seam.
- `1602.00731` (Limit-order book resiliency after effective market orders: Spread, depth and intensity) is worth another pass because it keeps appearing near the market_design_seams x refill_lag_local_shock seam.
- `1609.04620` (Price impact without order book: A study of the OTC credit index market) is worth another pass because it keeps appearing near the market_design_seams x parity_propagation_delayed_repair seam.
- `1609.04620` (Price impact without order book: A study of the OTC credit index market) is worth another pass because it keeps appearing near the parity_propagation_delayed_repair x refill_lag_resiliency seam.
- `1201.5448` (Determinants of immediate price impacts at the trade level in an emerging order-driven market) is worth another pass because it keeps appearing near the refill_lag_local_shock x refill_lag_resiliency seam.
- `1403.0842` (The adaptive nature of liquidity taking in limit order books) is worth another pass because it keeps appearing near the refill_lag_local_shock x refill_lag_resiliency seam.
- `2205.14699` (Managing Risk in DeFi Portfolios) is worth another pass because it keeps appearing near the near settlement, lexically far seam.
- `2201.08875` (Information-Based Trading) is worth another pass because it keeps appearing near the near auction design, lexically far seam.

## Publication Summary

Accepted findings in the broadened run: 9.
Rejected findings recorded with reasons: 2.
Near-miss papers still worth inspection: 15.
