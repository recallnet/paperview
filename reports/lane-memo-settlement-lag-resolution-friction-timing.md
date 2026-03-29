# Settlement-Lag / Resolution-Friction Timing

## Thesis

Execution opportunities may persist when trades clear economically before they settle legally or operationally, so timing edges should be modeled around collateral, margin, and resolution-state synchronization rather than around printed price gaps alone.

## Why This Lead Exists

The accepted settlement-resolution publication row says settlement frictions and market rules create a seam between economic execution and legal resolution. The broader research memo and DS2 bridge study both push the same claim: some consistency breaks remain tradeable because the post-trade state cannot synchronize immediately even when the market sees the mismatch.

## Supporting Papers

- `1811.08038` (Arbitrage Opportunities in CDS Term Structure: Theory and Implications for OTC Derivatives): supports the idea that apparent arbitrage can persist when derivative and credit-market state variables do not resolve on the same timetable.
- `1709.08238` (Counterparty Credit Limits: The Impact of a Risk-Mitigation Measure on Everyday Trading): shows that risk controls and counterparty limits can block immediate repair even in everyday trading.
- `1609.04620` (Price impact without order book: A study of the OTC credit index market): gives a market where impact and execution occur without a canonical order book, which makes legal or operational resolution timing more visible.
- `1101.3926` (Collateral Margining in Arbitrage-Free Counterparty Valuation Adjustment including Re-Hypotecation and Netting): grounds the collateral and netting side of the memo by making resolution state explicit instead of treating settlement as background plumbing.
- `1312.0128` (CCPs, Central Clearing, CSA, Credit Collateral and Funding Costs Valuation FAQ: Re-hypothecation, CVA, Closeout, Netting, WWR, Gap-Risk, Initial and Variation Margins, Multiple Discount Curves, FVA?): expands the post-trade state space into CCP, CSA, funding, margin, and closeout mechanics that can all delay practical repair.
- `2106.06389` (An Empirical Study of DeFi Liquidations: Incentives, Risks, and Instabilities) and `2009.13235` (Liquidations: DeFi on a Knife-edge): show that the same timing seam appears in thin or immature markets where liquidation and settlement mechanics are observable rather than hidden.

## Hypothesis

Basis, hedge slippage, or unwind opportunities should be more persistent and more executable when collateral, margin, or closeout state is out of sync with the economic trade state. Events with slower resolution-state synchronization should display wider repair windows than matched events with similar price deviations but cleaner settlement state.

## Data

- Execution timestamps and post-trade lifecycle events for at least one market with observable settlement or collateral state.
- Collateral, margin, liquidation, or closeout event markers aligned to the executed position lifecycle.
- Linked hedging or reference-market prices so the repair window can be measured against an external state.
- At least three months of data in one concrete venue family, such as CDS/credit, futures basis, or on-chain liquidation venues with observable settlement mechanics.

## Baseline

A price-only basis monitor that flags deviations and assumes repair depends only on spread, volatility, and liquidity, with no explicit model of settlement or resolution-state timing.

## Seam-Aware Program

Classify each event by both the economic trade state and the legal or operational resolution state. The first model should separate cleanly settled events from delayed-resolution events, then estimate whether delay state predicts basis persistence, unwind pressure, or hedge slippage after controlling for raw deviation size.

## First Test

Test whether settlement timing and venue-rule mismatches create repeatable basis or unwind windows around resolution events. Start with one product family, mark resolution-state transitions, and compare time-to-repair plus executable unwind quality between delayed-resolution and clean-resolution windows.

## Metric

Primary metric: repair-window length conditional on observed resolution friction. Secondary metrics: executable capture after fees, hedge slippage during the delay window, and forced-unwind pressure around margin or liquidation boundaries.

## Fail-Fast

- If the apparent edge disappears once true resolution-state timestamps are aligned, the signal was only a data-latency artifact.
- If settlement and collateral state cannot be observed with enough fidelity, this memo collapses into a generic basis-trading story.
- If resolution friction predicts persistence but not executable capture after fees and financing, the lead is descriptive rather than actionable.

## Stop / Go

Go if delayed-resolution events materially extend the repair window and improve executable capture relative to the price-only baseline. Stop if price deviation, volatility, and liquidity explain the full effect without any incremental contribution from settlement-state variables.

## Gap To Close

The remaining gap is synchronized post-trade state data. Without explicit collateral, margin, closeout, or liquidation timing, resolution friction is too easy to confuse with ordinary illiquidity.

