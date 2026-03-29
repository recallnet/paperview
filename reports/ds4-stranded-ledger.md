# DS4 Stranded Result Ledger

This study forces top stranded q-fin papers into explicit modern implementation paths instead of leaving them in theory language.

## Stop / Go

- stranded entries materialized: `15`
- executable-looking rescues: `8`
- success threshold met: `true`

## Rescue-Family Diversity

- calibration_speedup: `2`
- derivatives_surface: `2`
- execution_control: `2`
- funding_curve: `1`
- general_qfin: `2`
- macro_policy: `1`
- portfolio_control: `3`
- regime_timing: `1`
- risk_transfer: `1`

## Entries

## 1. 2204.08581 — On Parametric Optimal Execution and Machine Learning Surrogates

- home domain: `q-fin.TR`
- date: `2023-10-29`
- rescue family: `execution_control`
- confidence: `high`
- executable research task: `true`

Result plain: Machine-learning surrogates can speed the search for near-optimal execution schedules under parametric impact models.

Instrument assumed: algorithmic execution in liquid futures or equities

Why stranded then: The result is practical but remained stranded inside execution-model calibration language instead of being promoted as a deployable trading workflow.

Modern equivalent now: execution policy search with fast surrogates

First implementation test: Replicate the surrogate-assisted execution policy on newer fragmented limit-order-book data with realistic fees.

Gap to close: Need to show that the surrogate remains stable under venue fragmentation and regime shifts.

Why not just theory: The result already specifies a concrete modern replay or implementation comparison, so it can be evaluated as a live research task rather than only as a theorem.

## 2. 2106.00581 — $N$-player and Mean-field Games in Itô-diffusion Markets with Competitive or Homophilous Interaction

- home domain: `q-fin.MF`
- date: `2021-06-14`
- rescue family: `general_qfin`
- confidence: `medium`
- executable research task: `true`

Result plain: The paper offers a concrete illiquidity-aware execution control that still looks testable on modern data.

Instrument assumed: intraday optimal execution under temporary impact

Why stranded then: It reads like mathematical finance rather than a practitioner-ready execution template, so the result never surfaced as a live strategy clue.

Modern equivalent now: adaptive execution with impact-aware control

First implementation test: Re-estimate the proposed impact-aware control on current intraday data and compare it to simpler adaptive execution baselines.

Gap to close: Need evidence that the control law survives modern queue dynamics and hidden-liquidity behavior.

Why not just theory: The result already specifies a concrete modern replay or implementation comparison, so it can be evaluated as a live research task rather than only as a theorem.

## 3. 1712.10105 — Variance swaps under Lévy process with stochastic volatility and stochastic interest rate in incomplete markets

- home domain: `q-fin.PR`
- date: `2018-03-14`
- rescue family: `derivatives_surface`
- confidence: `low`
- executable research task: `false`

Result plain: The paper offers a pricing or hedging structure that may expose incomplete-market dislocations if translated into observable surface diagnostics.

Instrument assumed: listed or OTC derivatives with incomplete hedging and sparse market-making

Why stranded then: It remained trapped in valuation language instead of being translated into a screen for surface or hedge dislocations.

Modern equivalent now: surface-consistency or hedge-break monitor

First implementation test: Track whether the model-implied surface inconsistency predicts later repricing or hedge slippage in thin derivatives markets.

Gap to close: Need a direct mapping from the model variables to observable surface, borrow, and liquidity measurements.

Why not just theory: The result becomes testable once the model is recast as a monitor for observed surface breaks, though the implementation burden is higher than for execution papers.

## 4. 1903.06928 — Active and Passive Portfolio Management with Latent Factors

- home domain: `q-fin.PM`
- date: `2019-03-16`
- rescue family: `portfolio_control`
- confidence: `medium`
- executable research task: `true`

Result plain: The paper proposes a portfolio or factor control rule that may become useful when markets are thin, latent-state driven, or incompletely arbitraged.

Instrument assumed: multi-asset allocation or stat-arb books with latent-state risk

Why stranded then: It stayed in portfolio-construction language instead of being reframed as a live market-friction or timing task.

Modern equivalent now: state-aware portfolio throttle or inventory-risk overlay

First implementation test: Backtest the rule as a portfolio overlay during thin-liquidity or latent-factor stress windows rather than over the full sample.

Gap to close: Need a mapping from the latent-state model to observable market-stage or liquidity indicators.

Why not just theory: The proposal can be stress-tested as a concrete overlay on real portfolio paths and compared with simpler inventory or factor controls.

## 5. 2005.04297 — Pricing Path-Dependent Derivatives under Multiscale Stochastic Volatility Models: a Malliavin Representation

- home domain: `q-fin.CP`
- date: `2020-05-08`
- rescue family: `derivatives_surface`
- confidence: `low`
- executable research task: `false`

Result plain: The paper offers a pricing or hedging structure that may expose incomplete-market dislocations if translated into observable surface diagnostics.

Instrument assumed: listed or OTC derivatives with incomplete hedging and sparse market-making

Why stranded then: It remained trapped in valuation language instead of being translated into a screen for surface or hedge dislocations.

Modern equivalent now: surface-consistency or hedge-break monitor

First implementation test: Track whether the model-implied surface inconsistency predicts later repricing or hedge slippage in thin derivatives markets.

Gap to close: Need a direct mapping from the model variables to observable surface, borrow, and liquidity measurements.

Why not just theory: The result becomes testable once the model is recast as a monitor for observed surface breaks, though the implementation burden is higher than for execution papers.

## 6. 1909.13366 — Not so Particular about Calibration: Smile Problem Resolved

- home domain: `q-fin.MF`
- date: `2019-09-29`
- rescue family: `calibration_speedup`
- confidence: `low`
- executable research task: `true`

Result plain: The paper speeds model calibration or approximation in a way that might matter if calibration latency itself creates a missed execution or hedging opportunity.

Instrument assumed: derivatives desks or execution systems with repeated recalibration needs

Why stranded then: The contribution was presented as numerical convenience rather than as a way to shorten the decision loop.

Modern equivalent now: fast calibration proxy in a live decision loop

First implementation test: Test whether faster recalibration materially changes hedge or execution decisions during rapidly moving but thin markets.

Gap to close: Need evidence that calibration latency, not just model error, is the limiting operational bottleneck.

Why not just theory: It becomes concrete only if calibration speed changes a real trading or hedging decision, so this is an executable hypothesis but not yet a full workflow.

## 7. 1803.08160 — An Economic Bubble Model and Its First Passage Time

- home domain: `q-fin.MF`
- date: `2018-03-21`
- rescue family: `regime_timing`
- confidence: `low`
- executable research task: `false`

Result plain: The paper models a regime transition or bubble-timing process that may help detect fragile, weakly arbitraged market states before repair arrives.

Instrument assumed: speculative or thinly arbitraged markets with regime-switching risk

Why stranded then: It was framed as regime or bubble theory instead of a monitor for thin-market instability.

Modern equivalent now: fragility-regime timing indicator

First implementation test: Test whether the model’s regime signal identifies periods where cross-market repair slows or liquidity thins abruptly.

Gap to close: Need a stable mapping from latent regime variables to observable fragility signals.

Why not just theory: This is testable as a regime indicator, but it is further from direct implementation than the execution and contagion rescues.

## 8. 1603.00527 — Affine multiple yield curve models

- home domain: `q-fin.MF`
- date: `2017-02-07`
- rescue family: `funding_curve`
- confidence: `low`
- executable research task: `false`

Result plain: The paper describes a curve or calibration structure that may reveal funding-friction or basis seams in incomplete fixed-income markets.

Instrument assumed: rates, funding, or basis books with multiple curves and sparse liquidity

Why stranded then: It was left in rates-model calibration language, which obscured the market-friction timing angle.

Modern equivalent now: funding-curve stress monitor

First implementation test: Test whether curve-fit stress or multi-curve inconsistency predicts later basis repair in thin funding markets.

Gap to close: Need observable mapping from calibration stress to tradeable funding dislocations.

Why not just theory: The result is closer to a monitor than a ready strategy, but it still suggests a falsifiable timing diagnostic.

## 9. 2004.10096 — Wealth Effect on Portfolio Allocation in Incomplete Markets

- home domain: `q-fin.PM`
- date: `2021-08-26`
- rescue family: `portfolio_control`
- confidence: `medium`
- executable research task: `true`

Result plain: The paper proposes a portfolio or factor control rule that may become useful when markets are thin, latent-state driven, or incompletely arbitraged.

Instrument assumed: multi-asset allocation or stat-arb books with latent-state risk

Why stranded then: It stayed in portfolio-construction language instead of being reframed as a live market-friction or timing task.

Modern equivalent now: state-aware portfolio throttle or inventory-risk overlay

First implementation test: Backtest the rule as a portfolio overlay during thin-liquidity or latent-factor stress windows rather than over the full sample.

Gap to close: Need a mapping from the latent-state model to observable market-stage or liquidity indicators.

Why not just theory: The proposal can be stress-tested as a concrete overlay on real portfolio paths and compared with simpler inventory or factor controls.

## 10. 1604.08677 — An Explicit Formula for Likelihood Function for Gaussian Vector Autoregressive Moving-Average Model Conditioned on Initial Observables with Application to Model Calibration

- home domain: `q-fin.ST`
- date: `2016-04-29`
- rescue family: `calibration_speedup`
- confidence: `low`
- executable research task: `true`

Result plain: The paper speeds model calibration or approximation in a way that might matter if calibration latency itself creates a missed execution or hedging opportunity.

Instrument assumed: derivatives desks or execution systems with repeated recalibration needs

Why stranded then: The contribution was presented as numerical convenience rather than as a way to shorten the decision loop.

Modern equivalent now: fast calibration proxy in a live decision loop

First implementation test: Test whether faster recalibration materially changes hedge or execution decisions during rapidly moving but thin markets.

Gap to close: Need evidence that calibration latency, not just model error, is the limiting operational bottleneck.

Why not just theory: It becomes concrete only if calibration speed changes a real trading or hedging decision, so this is an executable hypothesis but not yet a full workflow.

## 11. 1809.11010 — Exact Solutions for Optimal Investment Strategies and Indifference Prices under Non-Differentiable Preferences

- home domain: `q-fin.PR`
- date: `2018-09-28`
- rescue family: `general_qfin`
- confidence: `low`
- executable research task: `false`

Result plain: The paper may hide a usable market-friction or implementation clue, but the rescue path is still underspecified.

Instrument assumed: q-fin.PR market setting

Why stranded then: The result remained in specialist q-fin language instead of being translated into an operational workflow.

Modern equivalent now: untranslated q-fin mechanism needing modern recast

First implementation test: Translate the core state variables into observable market features and test whether they predict a repeatable decision edge.

Gap to close: Need a clearer mapping from theory variables to observable market-state measurements.

Why not just theory: There is a plausible implementation path, but it is still too generic to count as a strong executable rescue yet.

## 12. 1910.12130 — Price mediated contagion through capital ratio requirements with VWAP liquidation prices

- home domain: `q-fin.MF`
- date: `2021-02-18`
- rescue family: `execution_control`
- confidence: `medium`
- executable research task: `true`

Result plain: The paper contains an execution or liquidation control that can be replayed as a concrete scheduling policy on modern market data.

Instrument assumed: fragmented equities, futures, or large-inventory liquidation books

Why stranded then: It was published as control, calibration, or optimal-execution theory rather than as an implementation memo.

Modern equivalent now: adaptive execution schedule or liquidation-control benchmark

First implementation test: Replay the control on modern intraday data against TWAP, POV, and simple imbalance-aware baselines.

Gap to close: Need modern venue-fragmentation, hidden-liquidity, and fee-model robustness checks.

Why not just theory: The control can be evaluated directly with historical order-book or execution-replay data, so it already defines a falsifiable implementation task.

## 13. 2304.08819 — Optimal moral-hazard-free reinsurance under extended distortion premium principles

- home domain: `q-fin.MF`
- date: `2023-04-18`
- rescue family: `risk_transfer`
- confidence: `low`
- executable research task: `false`

Result plain: The paper proposes a risk-transfer structure that may become useful when markets cannot clear risk quickly through standard liquidity providers.

Instrument assumed: insurance, reinsurance, or structured-risk transfer markets

Why stranded then: It stayed inside contract-design language rather than being converted into a timing or inventory-constraint workflow.

Modern equivalent now: risk-transfer stress overlay

First implementation test: Test whether the proposed structure improves risk transfer during thin-liquidity or delayed-repair regimes compared with vanilla hedges.

Gap to close: Need an operational setting where the contract terms can be approximated or simulated realistically.

Why not just theory: The idea can be simulated, but it is not yet as directly executable as the execution-control and contagion rescues.

## 14. 2106.06185 — Mean Field Portfolio Games

- home domain: `q-fin.MF`
- date: `2022-04-25`
- rescue family: `portfolio_control`
- confidence: `medium`
- executable research task: `true`

Result plain: The paper proposes a portfolio or factor control rule that may become useful when markets are thin, latent-state driven, or incompletely arbitraged.

Instrument assumed: multi-asset allocation or stat-arb books with latent-state risk

Why stranded then: It stayed in portfolio-construction language instead of being reframed as a live market-friction or timing task.

Modern equivalent now: state-aware portfolio throttle or inventory-risk overlay

First implementation test: Backtest the rule as a portfolio overlay during thin-liquidity or latent-factor stress windows rather than over the full sample.

Gap to close: Need a mapping from the latent-state model to observable market-stage or liquidity indicators.

Why not just theory: The proposal can be stress-tested as a concrete overlay on real portfolio paths and compared with simpler inventory or factor controls.

## 15. 1708.07996 — A Simple Algorithm for Solving Ramsey Optimal Policy with Exogenous Forcing Variables

- home domain: `q-fin.EC`
- date: `2017-08-26`
- rescue family: `macro_policy`
- confidence: `low`
- executable research task: `false`

Result plain: The paper contains a policy-control structure that is too far from a trading implementation to count as a near-term executable edge.

Instrument assumed: macro or policy-sensitive markets

Why stranded then: It belongs to policy design more than trading implementation.

Modern equivalent now: policy-regime sensitivity monitor

First implementation test: Check whether the policy-state proxy helps explain later thin-market dislocations, rather than trading it directly.

Gap to close: Need a much tighter bridge between policy variables and tradeable market states.

Why not just theory: This remains mainly theoretical for DS4 purposes and is included to keep the rescue queue honest about what is and is not executable.
