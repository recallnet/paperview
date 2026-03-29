# DS2 Bridge-Zone Mining

This study forces bridge families that should matter for diamond hunting in early, weakly arbitraged, or structurally immature markets.

## Stop / Go

- bridge zones materialized: `5`
- non-empty bridge zones beyond queue/refill: `5`
- success threshold met: `true`

## Candidate-Family Diversity

- auction_handoff_recovery: `10`
- settlement_parity_repair: `10`
- participant_design_pathologies: `10`
- queue_service_discipline: `10`
- defi_immature_repair: `10`

## Auction / Pari-Mutuel x Refill / Shock-Recovery

This bridge zone points to a post-uncrossing repair seam: auction and pari-mutuel papers appear alongside liquidity-shock and refill studies, suggesting that auction clearing conditions shape the first continuous-book refill regime. The strongest supporting papers currently include 2301.05677 (Price impact in equity auctions: zero, then linear), cond-mat/0210475 (Statistical theory of the continuous double auction), physics/0603084 (Relation between Bid-Ask Spread, Impact and Volatility in Double Auction Markets), which together imply that the exploitable edge is not auction pricing alone or refill alone, but the handoff between them.

Why neither side alone gives the full idea: Auction and pari-mutuel papers explain uncrossing and batch clearing, while refill and shock-recovery papers explain post-event book healing. Neither side alone tells you whether uncrossing conditions create a temporary quoting seam as the continuous book repopulates.

Translation questions:
- Does queue priority gained in the first post-uncrossing window price adverse selection differently than queue priority gained later in continuous trading?
- Which auction imbalance or clearing-price features predict slow versus fast depth refill after the switch back to continuous matching?
- Are post-auction liquidity crises best modeled as auction design failures, resiliency failures, or an interaction between the two?

Top papers:
- `2301.05677` | `composition` | `auction_handoff x refill_lag_local_shock` | Price impact in equity auctions: zero, then linear
- `cond-mat/0210475` | `composition` | `auction_parimutuel_design x refill_lag_local_shock` | Statistical theory of the continuous double auction
- `physics/0603084` | `composition` | `auction_handoff x refill_lag_local_shock` | Relation between Bid-Ask Spread, Impact and Volatility in Double Auction Markets
- `1506.03758` | `bridge` | `auction_parimutuel_design x refill_lag_local_shock` | From Walras' auctioneer to continuous time double auctions: A general dynamic theory of supply and demand
- `1208.3083` | `bridge` | `auction_parimutuel_design x refill_lag_local_shock` | Investor's sentiment in multi-agent model of the continuous double auction
- `1201.5448` | `composition` | `auction_handoff x refill_lag_resiliency` | Determinants of immediate price impacts at the trade level in an emerging order-driven market
- `0712.0912` | `composition` | `auction_handoff x refill_lag_local_shock` | Empirical regularities of order placement in the Chinese stock market
- `0906.1387` | `composition` | `auction_handoff x refill_lag_local_shock` | Asymmetric statistics of order books: The role of discreteness and evidence for strategic order placement
- `1802.01921` | `composition` | `auction_handoff x refill_lag_local_shock` | Dynamical regularities of US equities opening and closing auctions
- `1609.04620` | `composition` | `auction_handoff x refill_lag_resiliency` | Price impact without order book: A study of the OTC credit index market

## Settlement / Async-Repair x Parity / Consistency

This zone connects asynchronous settlement and collateral mechanics to parity and consistency failures across linked markets. The supporting papers 1811.08038 (Arbitrage Opportunities in CDS Term Structure: Theory and Implications for OTC Derivatives), 1709.08238 (Counterparty Credit Limits: The Impact of a Risk-Mitigation Measure on Everyday Trading), 1609.04620 (Price impact without order book: A study of the OTC credit index market) suggest that delayed repair is often a settlement-state problem, which means the edge comes from knowing when consistency cannot be restored immediately even if the mispricing is obvious.

Why neither side alone gives the full idea: Settlement and resolution papers explain delayed finality, collateral, and close-out mechanics, while parity and consistency papers explain when linked markets disagree. The bridge matters because asynchronous settlement is often the reason the inconsistency persists long enough to trade.

Translation questions:
- Which settlement frictions turn a nominal parity deviation into a durable, harvestable repair trade rather than a transient quote mismatch?
- Do CCP, collateral, or AMM liquidation rules explain why some cross-market inconsistencies remain open longer than others?
- Can parity-repair opportunities be ranked by the time it takes collateral or counterparty state to synchronize?

Top papers:
- `1811.08038` | `composition` | `settlement_resolution_seams x state_graph_inconsistencies` | Arbitrage Opportunities in CDS Term Structure: Theory and Implications for OTC Derivatives
- `1709.08238` | `composition` | `parity_propagation_delayed_repair x settlement_resolution_seams` | Counterparty Credit Limits: The Impact of a Risk-Mitigation Measure on Everyday Trading
- `1609.04620` | `composition` | `parity_propagation_delayed_repair x settlement_resolution_seams` | Price impact without order book: A study of the OTC credit index market
- `1101.3926` | `composition` | `settlement_resolution_seams x state_graph_inconsistencies` | Collateral Margining in Arbitrage-Free Counterparty Valuation Adjustment including Re-Hypotecation and Netting
- `1112.1607` | `composition` | `settlement_resolution_seams x state_graph_inconsistencies` | Restructuring Counterparty Credit Risk
- `2106.06389` | `composition` | `settlement_resolution_seams x state_graph_inconsistencies` | An Empirical Study of DeFi Liquidations: Incentives, Risks, and Instabilities
- `1312.0128` | `composition` | `settlement_resolution_seams x state_graph_inconsistencies` | CCPs, Central Clearing, CSA, Credit Collateral and Funding Costs Valuation FAQ: Re-hypothecation, CVA, Closeout, Netting, WWR, Gap-Risk, Initial and Variation Margins, Multiple Discount Curves, FVA?
- `2304.08590` | `composition` | `amm_settlement_latency x state_graph_inconsistencies` | Risks and opportunities in arbitrage and market-making in blockchain-based currency markets. Part 1 : Risks
- `2106.14404` | `composition` | `settlement_resolution_seams x state_graph_inconsistencies` | UNISWAP: Impermanent Loss and Risk Profile of a Liquidity Provider
- `1404.7314` | `composition` | `settlement_resolution_seams x state_graph_inconsistencies` | Nonlinear Valuation under Collateral, Credit Risk and Funding Costs: A Numerical Case Study Extending Black-Scholes

## Participant-Pathology x Market-Design

This bridge zone says participant behavior becomes more predictable when market rules expose or amplify it. The supporting papers 0908.0202 (Market impact and trading profile of large trading orders in stock markets), 1903.12458 (Market Manipulation as a Security Problem), 1311.4160 (Simulating the Synchronizing Behavior of High-Frequency Trading in Multiple Markets) frame the opportunity as a rule-behavior interaction problem: design choices around priority, latency, or auctions determine whether toxic or manipulative flow leaves repeatable signatures.

Why neither side alone gives the full idea: Participant-pathology papers explain who behaves badly or predictably, and market-design papers explain which rules shape order handling. The bridge is the operational question: which rules amplify or suppress predictable bad behavior enough to create repeatable edge?

Translation questions:
- Which venue rules make informed, latency-sensitive, or manipulative flow most visible to passive or reactive strategies?
- Do tick-size, priority, or auction rules change the persistence of participant-driven imbalance signals?
- Which participant pathologies become tradeable only after they interact with a specific market-design seam?

Top papers:
- `0908.0202` | `composition` | `market_design_seams x participant_pathologies` | Market impact and trading profile of large trading orders in stock markets
- `1903.12458` | `composition` | `market_design_seams x participant_pathologies` | Market Manipulation as a Security Problem
- `1311.4160` | `composition` | `market_design_seams x participant_pathologies` | Simulating the Synchronizing Behavior of High-Frequency Trading in Multiple Markets
- `2006.08682` | `composition` | `market_design_seams x participant_pathologies` | The Importance of Low Latency to Order Book Imbalance Trading Strategies
- `2009.02808` | `composition` | `market_design_seams x participant_pathologies` | Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants
- `1212.4770` | `composition` | `market_design_seams x participant_pathologies` | Market Impact with Autocorrelated Order Flow under Perfect Competition
- `2003.04425` | `composition` | `market_design_seams x participant_pathologies` | Informed trading, limit order book and implementation shortfall: equilibrium and asymptotics
- `2012.12555` | `composition` | `market_design_seams x participant_pathologies` | Market Impact in Trader-Agents: Adding Multi-Level Order-Flow Imbalance-Sensitivity to Automated Trading Systems
- `1109.2631` | `bridge` | `market_design_seams x participant_pathologies` | Optimal trade execution and price manipulation in order books with time-varying liquidity
- `1207.2946` | `composition` | `market_design_seams x participant_pathologies` | Microscopic understanding of heavy-tailed return distributions in an agent-based model

## Queue-Value x Overloaded / Service-Discipline

This zone broadens queue value beyond normal-book microstructure by tying it to changing service discipline under automation, participant load, and venue evolution. The papers 1007.2352 (Automated Liquidity Provision and the Demise of Traditional Market Making), 2105.00521 (Order flow and price formation), 1806.05101 (Order-book modelling and market making strategies) imply that queue value is only dependable when the effective matching discipline is understood, especially in markets where overload, latency, or professionalization shift who actually gets served first.

Why neither side alone gives the full idea: Queue-value papers explain why position in line matters, but they usually assume a stable service discipline. Lifecycle, design, and participant-load papers explain when the matching engine, participant mix, or latency regime changes the effective service discipline itself.

Translation questions:
- When does queue position stop approximating time priority because the venue is effectively overloaded or dominated by faster actors?
- Which market-making signals survive when service discipline is distorted by latency, batching, or concentrated participant load?
- Can queue-value be conditioned on venue maturity or overload proxies without collapsing back to naive spread-based quoting?

Top papers:
- `1007.2352` | `composition` | `lifecycle_professionalization x queue_value_passive_quoting` | Automated Liquidity Provision and the Demise of Traditional Market Making
- `2105.00521` | `composition` | `market_design_seams x queue_value_passive_quoting` | Order flow and price formation
- `1806.05101` | `composition` | `participant_pathologies x queue_value_passive_quoting` | Order-book modelling and market making strategies
- `2109.15110` | `composition` | `market_design_seams x queue_value_passive_quoting` | Deep Hawkes Process for High-Frequency Market Making
- `1212.4770` | `composition` | `market_design_seams x queue_value_passive_quoting` | Market Impact with Autocorrelated Order Flow under Perfect Competition
- `2101.03086` | `composition` | `market_design_seams x queue_value_passive_quoting` | Market Making with Stochastic Liquidity Demand: Simultaneous Order Arrival and Price Change Forecasts
- `2006.08682` | `composition` | `market_design_seams x queue_value_passive_quoting` | The Importance of Low Latency to Order Book Imbalance Trading Strategies
- `1104.0587` | `composition` | `market_design_seams x queue_value_passive_quoting` | How does the market react to your order flow?
- `2108.07806` | `composition` | `lifecycle_professionalization x queue_value_passive_quoting` | Simulation and estimation of an agent-based market-model with a matching engine
- `1210.5781` | `composition` | `lifecycle_professionalization x queue_value_passive_quoting` | High Frequency Market Making

## DeFi / Bridge / Liquidation x Immature-Market Repair

This bridge zone ties immature-market repair problems to DeFi and other thin venues where rules, settlement, and liquidity are still co-evolving. The strongest supporting papers 2103.08842 (The Adoption of Blockchain-based Decentralized Exchanges), 2106.08157 (CeFi vs. DeFi -- Comparing Centralized to Decentralized Finance), 2009.13235 (Liquidations: DeFi on a Knife-edge) suggest that some on-chain edges are really early-market repair seams that persist because the market is not yet professionalized enough to close them quickly.

Why neither side alone gives the full idea: DeFi, bridge, and liquidation papers explain immature-market plumbing, while lifecycle and repair papers explain how young markets eventually harden. The seam is in markets that are still too thin or underspecified for arbitrage to close the failure mode immediately.

Translation questions:
- Which DeFi liquidation or bridge failures are really immature-market repair problems rather than purely smart-contract problems?
- What closes these seams first in practice: professionalized liquidity, rule changes, faster settlement, or cross-venue competition?
- Which repair dynamics from early electronic markets transfer cleanly into current thin on-chain venues?

Top papers:
- `2103.08842` | `composition` | `lifecycle_professionalization x market_design_seams` | The Adoption of Blockchain-based Decentralized Exchanges
- `2106.08157` | `composition` | `amm_settlement_latency x settlement_resolution_seams` | CeFi vs. DeFi -- Comparing Centralized to Decentralized Finance
- `2009.13235` | `composition` | `amm_settlement_latency x settlement_resolution_seams` | Liquidations: DeFi on a Knife-edge
- `2101.08778` | `composition` | `amm_settlement_latency x settlement_resolution_seams` | SoK: Decentralized Finance (DeFi)
- `2106.06389` | `composition` | `amm_settlement_latency x settlement_resolution_seams` | An Empirical Study of DeFi Liquidations: Incentives, Risks, and Instabilities
- `2212.10308` | `composition` | `amm_settlement_latency x settlement_resolution_seams` | DeFi Risk Transfer: Towards A Fully Decentralized Insurance Protocol
- `2303.15162` | `composition` | `amm_settlement_latency x settlement_resolution_seams` | Mitigating Decentralized Finance Liquidations with Reversible Call Options
- `2304.01918` | `composition` | `amm_settlement_latency x settlement_resolution_seams` | Decentralized Finance (DeFi)
- `2202.07742` | `bridge` | `amm_settlement_latency x settlement_resolution_seams` | A Short Survey on Business Models of Decentralized Finance (DeFi) Protocols
- `2206.08401` | `bridge` | `amm_settlement_latency x settlement_resolution_seams` | Is decentralized finance actually decentralized? A social network analysis of the Aave protocol on the Ethereum blockchain
