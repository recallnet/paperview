# Market-Design Delayed Parity Repair

## Thesis

Cross-market parity breaks may last materially longer when linked venues enforce different protection, priority, or tick rules, so repair timing should be modeled as a venue-design state variable rather than as generic arbitrage latency.

## Why This Lead Exists

The accepted market-design publication row says rule differences change how quickly linked markets repair temporary inconsistencies. The adjacent transition-state evidence says the edge lives at the repair boundary itself, not in ordinary spread mean reversion. Together, they point to a lane where venue design shapes when a visible inconsistency can actually close.

## Supporting Papers

- `1609.04620` (Price impact without order book: A study of the OTC credit index market): supports the idea that price impact and repair can behave differently when the market structure is not a simple continuous order book.
- `1811.08038` (Arbitrage Opportunities in CDS Term Structure: Theory and Implications for OTC Derivatives): shows that consistency breaks can persist when derivative and credit market state variables do not synchronize cleanly.
- `1709.08238` (Counterparty Credit Limits: The Impact of a Risk-Mitigation Measure on Everyday Trading): provides a concrete rule-layer example where risk-mitigation mechanics change everyday trading behavior and therefore likely change repair speed.
- `2011.04367` (Comparing the market microstructure between two South African exchanges): gives a direct venue-comparison surface where differing exchange rules can be aligned with convergence timing outcomes.
- `2004.12011` (Trading Foreign Exchange Triplets): grounds the state-graph side of the memo by treating linked-market consistency as a repair problem rather than a single-market signal.

## Hypothesis

When two related venues or instruments disagree on price, basis, or implied state, the repair window will be longer and more tradeable when venue rules differ on priority, tick size, protection, or risk controls. The same raw mispricing should repair faster when the rule set is symmetric.

## Data

- Two or more linked venues or instruments with synchronized quote and trade timestamps.
- Venue-rule metadata: tick size regime, order-priority rule, auction/protection status, market-order protection, and any counterparty or risk-control constraints that can block immediate repair.
- Full-depth or top-of-book reconstruction around detected parity breaks.
- At least three months of data for one concrete linked pair, such as dual-listed equities, cash/futures, ETF/NAV proxies, or cross-venue FX/crypto pairs.

## Baseline

A naive parity monitor that flags deviations above a fixed spread or basis threshold and assumes repair speed depends only on deviation size, volatility, and liquidity, without any venue-design state.

## Seam-Aware Program

Track parity breaks jointly with venue-design asymmetry. The first concrete model should classify each event by rule mismatch features such as asymmetric tick size, different priority rules, or protection/auction state mismatch, then estimate whether repair speed, quote fade, and executable convergence differ from matched symmetric-rule events.

## First Test

Compare venue rule differences against delayed cross-market convergence after local dislocations. Start with one linked pair, define a parity break, measure time-to-repair, and test whether rule-mismatch windows have slower repair or more favorable execution than matched same-rule windows.

## Metric

Primary metric: repair-time delta between rule-mismatch and rule-symmetric events, conditioned on deviation size and contemporaneous liquidity. Secondary metrics: executable capture after fees, quote fade before repair, and adverse selection after entering the convergence trade.

## Fail-Fast

- If repair timing is fully explained by volatility and liquidity once rule variables are added, this is not a market-design seam.
- If the result depends on stale timestamps or unaligned feeds, the seam is a data artifact rather than a venue-rule effect.
- If execution cannot be achieved before repair because the relevant venue is too thin or too protected, the lead remains descriptive rather than tradeable.

## Stop / Go

Go if at least one rule-mismatch feature materially widens the repair window and improves executable capture relative to the naive parity baseline. Stop if the effect disappears after controlling for event size, venue liquidity, and time-of-day state.

## Gap To Close

The remaining gap is a clean venue-rule panel aligned to repair events. Without explicit rule-state annotations, delayed parity repair can still be mistaken for generic fragmentation noise.

