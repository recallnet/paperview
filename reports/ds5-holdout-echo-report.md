# DS5 Holdout Echo Report

This study checks whether top pre-2024 candidates from the DS study stack echo meaningfully in later 2024+ market-adjacent papers.

## Stop / Go

- pre-2024 candidates evaluated: `51`
- meaningful echoes (`validation` or `partial`): `26`
- success threshold met: `true`

## Candidate-Family Diversity

- calibration_speedup: `2`
- derivatives_surface: `2`
- execution_control: `2`
- funding_curve: `1`
- general_qfin: `2`
- lifecycle: `6`
- macro_policy: `1`
- participant_design_failure: `1`
- portfolio_control: `3`
- queue_refill_repair: `3`
- regime_timing: `1`
- risk_transfer: `1`
- settlement_async_repair: `12`
- settlement_resolution: `4`
- state_graph: `8`
- state_graph_repair: `1`
- thin_market_professionalization: `1`

## Verdict Mix

- partial: `21`
- unrelated: `25`
- validation: `5`

## Top Candidates

- `2105.13822` | `lifecycle` | `validation` | score `0.810904`
  candidate: Behavior of Liquidity Providers in Decentralized Exchanges
  top echo: 2410.19107 — What Drives Liquidity on Decentralized Exchanges? Evidence from the Uniswap Protocol
  why it matters: Professionalization lag leaves early-market rule seams unclosed
- `1212.4770` | `state_graph` | `validation` | score `0.798408`
  candidate: Market Impact with Autocorrelated Order Flow under Perfect Competition
  top echo: 2501.17096 — Why is the estimation of metaorder impact with public market data so challenging?
  why it matters: Cross-market state disagreement survives longer than naive arbitrage expects
- `1910.12130` | `execution_control` | `validation` | score `0.783807`
  candidate: Price mediated contagion through capital ratio requirements with VWAP liquidation prices
  top echo: 2311.05977 — Price-mediated contagion with endogenous market liquidity
  why it matters: adaptive execution schedule or liquidation-control benchmark
- `2304.08819` | `risk_transfer` | `validation` | score `0.761567`
  candidate: Optimal moral-hazard-free reinsurance under extended distortion premium principles
  top echo: 2504.17468 — Optimal design of reinsurance contracts with a continuum of risk assessments
  why it matters: risk-transfer stress overlay
- `2106.06185` | `portfolio_control` | `validation` | score `0.760484`
  candidate: Mean Field Portfolio Games
  top echo: 2311.02690 — Relative Arbitrage Opportunities in an Extended Mean Field System
  why it matters: state-aware portfolio throttle or inventory-risk overlay
- `1609.04620` | `queue_refill_repair` | `partial` | score `0.746785`
  candidate: Price impact without order book: A study of the OTC credit index market
  top echo: 2501.17096 — Why is the estimation of metaorder impact with public market data so challenging?
  why it matters: not in realized_market corpus; matched lexical-far probe near participant pathology, far realized-market q-fin
- `2108.07806` | `lifecycle` | `partial` | score `0.745577`
  candidate: Simulation and estimation of an agent-based market-model with a matching engine
  top echo: 2505.15296 — Agent-based Liquidity Risk Modelling for Financial Markets
  why it matters: Professionalization lag leaves early-market rule seams unclosed
- `2310.14320` | `settlement_resolution` | `partial` | score `0.73603`
  candidate: Analysis of the RMM-01 Market Maker
  top echo: 2409.11339 — A Derivative Pricing Perspective on Liquidity Tokens in Constant Product Market Makers
  why it matters: Execution-finality gap leaves repair trades open
- `2106.06389` | `settlement_async_repair` | `partial` | score `0.731574`
  candidate: An Empirical Study of DeFi Liquidations: Incentives, Risks, and Instabilities
  top echo: 2602.12104 — Liquidation Dynamics in DeFi and the Role of Transaction Fees
  why it matters: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `2204.11107` | `settlement_async_repair` | `partial` | score `0.728703`
  candidate: Debt-Financed Collateral and Stability Risks in the DeFi Ecosystem
  top echo: 2512.11976 — Institutionalizing risk curation in decentralized credit
  why it matters: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `2312.01018` | `settlement_async_repair` | `partial` | score `0.719434`
  candidate: Decentralized Finance: Protocols, Risks, and Governance
  top echo: 2512.00142 — DeFi TrustBoost: Blockchain and AI for Trustworthy Decentralized Financial Decisions
  why it matters: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `1702.08029` | `lifecycle` | `partial` | score `0.715444`
  candidate: The short-term price impact of trades is universal
  top echo: 2501.17096 — Why is the estimation of metaorder impact with public market data so challenging?
  why it matters: Professionalization lag leaves early-market rule seams unclosed
- `2106.08157` | `settlement_async_repair` | `partial` | score `0.715034`
  candidate: CeFi vs. DeFi -- Comparing Centralized to Decentralized Finance
  top echo: 2311.17715 — Market Misconduct in Decentralized Finance (DeFi): Analysis, Regulatory Challenges and Policy Implications
  why it matters: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `2106.00581` | `general_qfin` | `partial` | score `0.712802`
  candidate: $N$-player and Mean-field Games in Itô-diffusion Markets with Competitive or Homophilous Interaction
  top echo: 2311.02690 — Relative Arbitrage Opportunities in an Extended Mean Field System
  why it matters: adaptive execution with impact-aware control
- `2005.04297` | `derivatives_surface` | `partial` | score `0.708085`
  candidate: Pricing Path-Dependent Derivatives under Multiscale Stochastic Volatility Models: a Malliavin Representation
  top echo: 2006.01542 — Explicit approximations of option prices via Malliavin calculus in a general stochastic volatility framework
  why it matters: surface-consistency or hedge-break monitor
- `1003.0168` | `queue_refill_repair` | `partial` | score `0.708062`
  candidate: Order flow dynamics around extreme price changes on an emerging stock market
  top echo: 2506.07711 — The Subtle Interplay between Square-root Impact, Order Imbalance & Volatility: A Unifying Framework
  why it matters: not in realized_market corpus; matched lexical-far probe near market design, far realized-market q-fin
- `2108.00242` | `state_graph` | `partial` | score `0.706187`
  candidate: The Inelastic Market Hypothesis: A Microstructural Interpretation
  top echo: 2508.06788 — Returns and Order Flow Imbalances: Intraday Dynamics and Macroeconomic News Effects
  why it matters: Cross-market state disagreement survives longer than naive arbitrage expects
- `2204.08581` | `execution_control` | `partial` | score `0.702805`
  candidate: On Parametric Optimal Execution and Machine Learning Surrogates
  top echo: 2501.15106 — Solving Optimal Execution Problems via In-Context Operator Networks
  why it matters: execution policy search with fast surrogates
- `2107.14678` | `settlement_async_repair` | `partial` | score `0.702383`
  candidate: Financial intermediation and risk in decentralized lending protocols
  top echo: 2512.11976 — Institutionalizing risk curation in decentralized credit
  why it matters: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `1909.13366` | `calibration_speedup` | `partial` | score `0.6918`
  candidate: Not so Particular about Calibration: Smile Problem Resolved
  top echo: 2510.19126 — An Efficient Calibration Framework for Volatility Derivatives under Rough Volatility with Jumps
  why it matters: fast calibration proxy in a live decision loop
- `2212.07306` | `settlement_resolution` | `partial` | score `0.690963`
  candidate: Toxic Liquidation Spirals
  top echo: 2602.12104 — Liquidation Dynamics in DeFi and the Role of Transaction Fees
  why it matters: Execution-finality gap leaves repair trades open
- `1602.00731` | `queue_refill_repair` | `partial` | score `0.690538`
  candidate: Limit-order book resiliency after effective market orders: Spread, depth and intensity
  top echo: 2508.06788 — Returns and Order Flow Imbalances: Intraday Dynamics and Macroeconomic News Effects
  why it matters: not in realized_market corpus; matched lexical-far probe near market design, far realized-market q-fin
- `1007.2352` | `lifecycle` | `partial` | score `0.687059`
  candidate: Automated Liquidity Provision and the Demise of Traditional Market Making
  top echo: 2407.16885 — Automated Market Making and Decentralized Finance
  why it matters: Professionalization lag leaves early-market rule seams unclosed
- `1610.08767` | `state_graph` | `partial` | score `0.684499`
  candidate: Equity Market Impact Modeling: an Empirical Analysis for Chinese Market
  top echo: 2501.17096 — Why is the estimation of metaorder impact with public market data so challenging?
  why it matters: Cross-market state disagreement survives longer than naive arbitrage expects
- `2012.13230` | `settlement_async_repair` | `partial` | score `0.682157`
  candidate: SoK: Lending Pools in Decentralized Finance
  top echo: 2512.11976 — Institutionalizing risk curation in decentralized credit
  why it matters: not in realized_market corpus; home domain cs.CR is outside q-fin; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `1903.06928` | `portfolio_control` | `partial` | score `0.680658`
  candidate: Active and Passive Portfolio Management with Latent Factors
  top echo: 2502.17915 — Dynamic Factor Model-Based Multiperiod Mean-Variance Portfolio Selection with Portfolio Constraints
  why it matters: state-aware portfolio throttle or inventory-risk overlay
- `1905.05310` | `settlement_async_repair` | `unrelated` | score `0.672562`
  candidate: On the consistency of jump-diffusion dynamics for FX rates under inversion
  top echo: 2308.15672 — Asymptotics for Short Maturity Asian Options in Jump-Diffusion models with Local Volatility
  why it matters: not in realized_market corpus; matched lexical-far probe near state-graph inconsistency, far realized-market q-fin
- `2007.07998` | `state_graph` | `unrelated` | score `0.672331`
  candidate: Transaction Costs in Execution Trading
  top echo: 2405.07184 — Trade execution games in a Markovian environment
  why it matters: Cross-market state disagreement survives longer than naive arbitrage expects
- `1104.3616` | `state_graph` | `unrelated` | score `0.670354`
  candidate: Strategies used as spectroscopy of financial markets reveal new stylized facts
  top echo: 2504.08611 — International Financial Markets Through 150 Years: Evaluating Stylized Facts
  why it matters: Cross-market state disagreement survives longer than naive arbitrage expects
- `cond-mat/9808240` | `state_graph` | `unrelated` | score `0.666977`
  candidate: Scaling Laws for the Market Microstructure of the Interdealer Broker Markets
  top echo: 2303.08867 — A Bayesian theory of market impact
  why it matters: Cross-market state disagreement survives longer than naive arbitrage expects
- `1108.1632` | `participant_design_failure` | `unrelated` | score `0.662354`
  candidate: Why is order flow so persistent?
  top echo: 2601.11602 — The Physics of Price Discovery: Deconvolving Information, Volatility, and the Critical Breakdown of Signal during Retail Herding
  why it matters: not in realized_market corpus; matched lexical-far probe near market design, far realized-market q-fin
- `1910.02194` | `settlement_async_repair` | `unrelated` | score `0.660558`
  candidate: Liquidity in Credit Networks with Constrained Agents
  top echo: 2410.18145 — A minimal model of money creation under regulatory constraints
  why it matters: not in realized_market corpus; home domain cs.GT is outside q-fin; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `1803.08160` | `regime_timing` | `unrelated` | score `0.649118`
  candidate: An Economic Bubble Model and Its First Passage Time
  top echo: 2502.10101 — What are Asset Price Bubbles? A Survey on Definitions of Financial Bubbles
  why it matters: fragility-regime timing indicator
- `1810.01736` | `settlement_resolution` | `unrelated` | score `0.645479`
  candidate: Auction Theory Adaptations for Real Life Applications
  top echo: 2603.16333 — Open vs. Sealed: Auction Format Choice for Maximal Extractable Value
  why it matters: Execution-finality gap leaves repair trades open
- `2004.10096` | `portfolio_control` | `unrelated` | score `0.643135`
  candidate: Wealth Effect on Portfolio Allocation in Incomplete Markets
  top echo: 2208.14152 — Value-at-Risk constrained portfolios in incomplete markets: a dynamic programming approach to Heston's model
  why it matters: state-aware portfolio throttle or inventory-risk overlay
- `1206.5324` | `lifecycle` | `unrelated` | score `0.641116`
  candidate: Effective Trade Execution
  top echo: 2509.01683 — The Impact of Sequential versus Parallel Clearing Mechanisms in Agent-Based Simulations of Artificial Limit Order Book Exchanges
  why it matters: Professionalization lag leaves early-market rule seams unclosed
- `physics/0702210` | `state_graph` | `unrelated` | score `0.641022`
  candidate: The tick-by-tick dynamical consistency of price impact in limit order books
  top echo: 1902.10743 — From Glosten-Milgrom to the whole limit order book and applications to financial regulation
  why it matters: Cross-market state disagreement survives longer than naive arbitrage expects
- `1104.0587` | `thin_market_professionalization` | `unrelated` | score `0.636042`
  candidate: How does the market react to your order flow?
  top echo: 2412.20847 — Strategic Learning and Trading in Broker-Mediated Markets
  why it matters: not in realized_market corpus; matched lexical-far probe near market design, far realized-market q-fin
- `2011.04367` | `state_graph` | `unrelated` | score `0.632996`
  candidate: Comparing the market microstructure between two South African exchanges
  top echo: 2510.22834 — Deviations from Tradition: Stylized Facts in the Era of DeFi
  why it matters: Cross-market state disagreement survives longer than naive arbitrage expects
- `1301.6115` | `settlement_async_repair` | `unrelated` | score `0.627237`
  candidate: DebtRank-transparency: Controlling systemic risk in financial networks
  top echo: 2506.16648 — Optimal Regulation and Investment Incentives in Financial Networks
  why it matters: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `1811.08949` | `settlement_resolution` | `unrelated` | score `0.627004`
  candidate: The transmission of liquidity shocks via China's segmented money market: evidence from recent market events
  top echo: 2601.08263 — A Blessing in Disguise: How DeFi Hacks Trigger Unintended Liquidity Injections into US Money Markets
  why it matters: Execution-finality gap leaves repair trades open
- `2104.09309` | `state_graph_repair` | `unrelated` | score `0.624869`
  candidate: Foreign exchange markets: price response and spread impact
  top echo: 2404.11722 — Beyond the Bid-Ask: Strategic Insights into Spread Prediction and the Global Mid-Price Phenomenon
  why it matters: not in realized_market corpus; matched lexical-far probe near state-graph inconsistency, far realized-market q-fin
- `1712.10105` | `derivatives_surface` | `unrelated` | score `0.624439`
  candidate: Variance swaps under Lévy process with stochastic volatility and stochastic interest rate in incomplete markets
  top echo: 2304.06202 — Filtration Reduction and Completeness in Jump-Diffusion Models
  why it matters: surface-consistency or hedge-break monitor
- `1603.00527` | `funding_curve` | `unrelated` | score `0.621064`
  candidate: Affine multiple yield curve models
  top echo: 2401.11619 — The geometry of multi-curve interest rate models
  why it matters: funding-curve stress monitor
- `physics/0608016` | `settlement_async_repair` | `unrelated` | score `0.618981`
  candidate: Market Efficiency in Foreign Exchange Markets
  top echo: 2404.16449 — Analysis of market efficiency in main stock markets: using Karman-Filter as an approach
  why it matters: not in realized_market corpus; home domain physics.soc-ph is outside q-fin; matched lexical-far probe near state-graph inconsistency, far realized-market q-fin
- `1809.11010` | `general_qfin` | `unrelated` | score `0.615173`
  candidate: Exact Solutions for Optimal Investment Strategies and Indifference Prices under Non-Differentiable Preferences
  top echo: 2512.21149 — Equilibrium investment under dynamic preference uncertainty
  why it matters: untranslated q-fin mechanism needing modern recast
- `2012.10262` | `lifecycle` | `unrelated` | score `0.612168`
  candidate: Matching in size: How market impact depends on the concentration of trading
  top echo: 2408.02634 — CLVR Ordering of Transactions on AMMs
  why it matters: Professionalization lag leaves early-market rule seams unclosed
- `cond-mat/9906343` | `settlement_async_repair` | `unrelated` | score `0.597485`
  candidate: Indeterminacy in foreign exchange market
  top echo: 2101.09738 — Volatility Shocks and Currency Returns
  why it matters: not in realized_market corpus; home domain cond-mat.stat-mech is outside q-fin; matched lexical-far probe near state-graph inconsistency, far realized-market q-fin
- `2309.06711` | `settlement_async_repair` | `unrelated` | score `0.587214`
  candidate: Epps Effect and the Signature of Short-Term Momentum Traders
  top echo: 2503.01629 — A New Traders' Game? -- Empirical Analysis of Response Functions in a Historical Perspective
  why it matters: not in realized_market corpus; matched lexical-far probe near state-graph inconsistency, far realized-market q-fin
- `1604.08677` | `calibration_speedup` | `unrelated` | score `0.541354`
  candidate: An Explicit Formula for Likelihood Function for Gaussian Vector Autoregressive Moving-Average Model Conditioned on Initial Observables with Application to Model Calibration
  top echo: 2405.00576 — Calibration of the rating transition model for high and low default portfolios
  why it matters: fast calibration proxy in a live decision loop
- `1708.07996` | `macro_policy` | `unrelated` | score `0.478138`
  candidate: A Simple Algorithm for Solving Ramsey Optimal Policy with Exogenous Forcing Variables
  top echo: 2603.10569 — Win-score promotion gates in aggregator-routed RFQ markets: A two-tier stochastic control model
  why it matters: policy-regime sensitivity monitor
