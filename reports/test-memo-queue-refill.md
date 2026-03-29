# Post-Shock Passive Quoting: Queue Value x Refill Lag

## Thesis

There may be positive passive-quoting edge immediately after local shocks when queue position is still favorable and displayed depth refills quickly, while the same setup becomes adverse when refill lags and maker participation falls away.

## Supporting Papers

- `1902.10743` (From Glosten-Milgrom to the whole limit order book and applications to financial regulation)
- `2408.03181` (Correlation emergence in two coupled simulated limit order books)
- `2406.04969` (An Algebraic Framework for the Modeling of Limit Order Books)
- `2009.02808` (Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants)
- `1005.0182` (A Multi Agent Model for the Limit Order Book Dynamics)

## Event Definitions

- Shock: either an absolute mid-price move greater than 3 rolling short-horizon sigma inside 5 seconds, or best-level displayed depth depletion greater than 40% on one side of the book inside 2 seconds.
- Refill: displayed depth at the best level and first two price levels recovering to at least 80% of the pre-shock depth baseline.
- Refill lag: elapsed time from the shock timestamp to 80% depth recovery.

## Features

- Queue position at shock time, measured in shares or contracts ahead at the posting level.
- Refill lag, measured as time to 80% depth recovery.
- Pre-shock displayed depth at the best level and first two levels.
- Post-shock spread in ticks and notional terms.
- Maker count change around the shock window, using unique visible liquidity providers when available or proxy quote-source counts when not.

## Baseline Policy

Naive spread-based passive posting: post passively at the best bid or ask whenever the spread is above a fixed threshold, with no conditioning on queue position, refill state, or maker withdrawal.

## Seam-Aware Policy

Post passively only when queue position is inside a favorable bound and refill is already recovering. A concrete first pass is: only join or keep a passive quote when queue position is in the front 20% of visible queue and refill lag is below 2 seconds, while suppressing passive posting when refill lag exceeds 5 seconds or maker count drops sharply.

## Success Metric

Use fill-quality-adjusted expectancy, not fill rate. Compare baseline versus seam-aware policy on realized markout per fill net of fees, and explicitly decompose expectancy into fill probability, adverse selection after fill, and missed-trade opportunity cost.

## Data Requirements

- Full-depth limit-order-book snapshots or event-level reconstruction.
- Event markers for volatility shocks and depth depletion windows.
- At least one liquid equity or futures instrument.
- Minimum three months of data to cover multiple volatility regimes.

## Known Risks

- Refill lag measurement is venue-specific and can be distorted by hidden liquidity or iceberg replenishment.
- Queue-position advantage may not survive hidden liquidity, midpoint interaction, or internalization.
- A shock definition that is too broad will blur together informed price moves and purely mechanical dislocations.

