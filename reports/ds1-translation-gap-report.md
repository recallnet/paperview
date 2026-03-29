# DS1 Translation-Gap Search

This study ranks papers that are mechanically close to challenge capsules while remaining far from pre-2024 realized-market discourse.

## Stop / Go

- outside obvious q-fin / trading discourse in top 100: `21`
- success threshold met: `true`

## Candidate-Family Diversity

- participant_design_failure: `22`
- queue_refill_repair: `7`
- settlement_async_repair: `45`
- state_graph_repair: `6`
- thin_market_professionalization: `20`

## Translation-Kind Mix

- compositional: `62`
- speculative: `38`

## Home-Domain Mix

- cond-mat.other: `1`
- cond-mat.stat-mech: `5`
- cs.CE: `1`
- cs.CR: `3`
- cs.CY: `1`
- cs.GT: `2`
- econ.GN: `10`
- physics.soc-ph: `3`
- q-fin.CP: `1`
- q-fin.GN: `7`
- q-fin.MF: `3`
- q-fin.PM: `2`
- q-fin.PR: `4`
- q-fin.RM: `7`
- q-fin.ST: `5`
- q-fin.TR: `45`

## Top 20 Preview

- `1910.02194` | `settlement_async_repair` | `compositional` | score `6.801648`
  title: Liquidity in Credit Networks with Constrained Agents
  home domain: cs.GT
  far-from-realized: not in realized_market corpus; home domain cs.GT is outside q-fin; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `cond-mat/9906343` | `settlement_async_repair` | `compositional` | score `6.592969`
  title: Indeterminacy in foreign exchange market
  home domain: cond-mat.stat-mech
  far-from-realized: not in realized_market corpus; home domain cond-mat.stat-mech is outside q-fin; matched lexical-far probe near state-graph inconsistency, far realized-market q-fin
- `physics/0608016` | `settlement_async_repair` | `compositional` | score `6.581374`
  title: Market Efficiency in Foreign Exchange Markets
  home domain: physics.soc-ph
  far-from-realized: not in realized_market corpus; home domain physics.soc-ph is outside q-fin; matched lexical-far probe near state-graph inconsistency, far realized-market q-fin
- `1104.0587` | `thin_market_professionalization` | `compositional` | score `6.484244`
  title: How does the market react to your order flow?
  home domain: q-fin.TR
  far-from-realized: not in realized_market corpus; matched lexical-far probe near market design, far realized-market q-fin
- `1602.00731` | `queue_refill_repair` | `compositional` | score `6.475407`
  title: Limit-order book resiliency after effective market orders: Spread, depth and intensity
  home domain: q-fin.TR
  far-from-realized: not in realized_market corpus; matched lexical-far probe near market design, far realized-market q-fin
- `1003.0168` | `queue_refill_repair` | `compositional` | score `6.461229`
  title: Order flow dynamics around extreme price changes on an emerging stock market
  home domain: q-fin.TR
  far-from-realized: not in realized_market corpus; matched lexical-far probe near market design, far realized-market q-fin
- `2204.11107` | `settlement_async_repair` | `compositional` | score `6.454938`
  title: Debt-Financed Collateral and Stability Risks in the DeFi Ecosystem
  home domain: q-fin.TR
  far-from-realized: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `2312.01018` | `settlement_async_repair` | `compositional` | score `6.382543`
  title: Decentralized Finance: Protocols, Risks, and Governance
  home domain: q-fin.TR
  far-from-realized: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `2106.08157` | `settlement_async_repair` | `compositional` | score `6.362615`
  title: CeFi vs. DeFi -- Comparing Centralized to Decentralized Finance
  home domain: q-fin.GN
  far-from-realized: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `1108.1632` | `participant_design_failure` | `compositional` | score `6.347156`
  title: Why is order flow so persistent?
  home domain: q-fin.TR
  far-from-realized: not in realized_market corpus; matched lexical-far probe near market design, far realized-market q-fin
- `1609.04620` | `queue_refill_repair` | `compositional` | score `6.342476`
  title: Price impact without order book: A study of the OTC credit index market
  home domain: q-fin.TR
  far-from-realized: not in realized_market corpus; matched lexical-far probe near participant pathology, far realized-market q-fin
- `2107.14678` | `settlement_async_repair` | `compositional` | score `6.311844`
  title: Financial intermediation and risk in decentralized lending protocols
  home domain: q-fin.GN
  far-from-realized: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `2106.06389` | `settlement_async_repair` | `compositional` | score `6.268436`
  title: An Empirical Study of DeFi Liquidations: Incentives, Risks, and Instabilities
  home domain: q-fin.GN
  far-from-realized: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `2104.09309` | `state_graph_repair` | `compositional` | score `6.257669`
  title: Foreign exchange markets: price response and spread impact
  home domain: q-fin.ST
  far-from-realized: not in realized_market corpus; matched lexical-far probe near state-graph inconsistency, far realized-market q-fin
- `1301.6115` | `settlement_async_repair` | `compositional` | score `6.217899`
  title: DebtRank-transparency: Controlling systemic risk in financial networks
  home domain: q-fin.RM
  far-from-realized: not in realized_market corpus; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `2309.06711` | `settlement_async_repair` | `compositional` | score `6.156882`
  title: Epps Effect and the Signature of Short-Term Momentum Traders
  home domain: q-fin.MF
  far-from-realized: not in realized_market corpus; matched lexical-far probe near state-graph inconsistency, far realized-market q-fin
- `2012.13230` | `settlement_async_repair` | `speculative` | score `6.092952`
  title: SoK: Lending Pools in Decentralized Finance
  home domain: cs.CR
  far-from-realized: not in realized_market corpus; home domain cs.CR is outside q-fin; matched lexical-far probe near settlement and resolution, far realized-market q-fin
- `1905.05310` | `settlement_async_repair` | `compositional` | score `6.006583`
  title: On the consistency of jump-diffusion dynamics for FX rates under inversion
  home domain: q-fin.MF
  far-from-realized: not in realized_market corpus; matched lexical-far probe near state-graph inconsistency, far realized-market q-fin
- `2408.02634` | `participant_design_failure` | `speculative` | score `6.004616`
  title: CLVR Ordering of Transactions on AMMs
  home domain: cs.GT
  far-from-realized: not in realized_market corpus; home domain cs.GT is outside q-fin; matched lexical-far probe near market design, far realized-market q-fin
- `2401.01622` | `settlement_async_repair` | `speculative` | score `5.916909`
  title: Non-Atomic Arbitrage in Decentralized Finance
  home domain: cs.CE
  far-from-realized: not in realized_market corpus; home domain cs.CE is outside q-fin; matched lexical-far probe near state-graph inconsistency, far realized-market q-fin
