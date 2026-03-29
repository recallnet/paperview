# Maker-Retreat Regime Switch for Queue-Based Quoting

## Thesis

Queue-position value may degrade materially, or even flip sign, when makers withdraw under stress, so passive quoting logic should treat maker-retreat windows as a separate regime rather than as ordinary queue competition.

## Supporting Papers

- `1005.0182` (A Multi Agent Model for the Limit Order Book Dynamics)
- `2009.02808` (Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants)
- `2101.03086` (Market Making with Stochastic Liquidity Demand: Simultaneous Order Arrival and Price Change Forecasts)

## Maker Withdrawal Proxies

- Number of unique maker IDs or quote-source identifiers at the best levels, when available.
- Depth change rate at the best level and first two levels.
- Cancellation-rate spike over a short rolling window relative to normal conditions.
- Inventory-imbalance indicators or one-sided quote retreat proxies inferred from persistent depth withdrawal on one side.

## Regime Classifier

Start with a binary classifier: `normal` versus `maker_retreat`. Label a window as `maker_retreat` when at least two withdrawal proxies breach their rolling 90th percentile thresholds, then extend to a three-state classifier (`normal`, `stressed`, `maker_retreat`) if the binary split is too coarse.

## Test

Measure queue-position value as fill quality minus subsequent adverse selection. Then ask whether this value degrades materially, or turns negative, during maker-retreat regimes relative to normal regimes. The key comparison is not raw fill count but whether front-of-queue placement still buys good fills once makers start pulling away.

## Baseline

Unconditional queue-position value across all regimes, using the same fill-quality and markout calculations but without any regime conditioning.

## Success Metric

A regime-conditional fill-quality difference that survives transaction-cost and adverse-selection controls. Success means queue-position value is measurably worse in maker-retreat windows than in normal windows, and the difference remains after controlling for spread, volatility, and instrument fixed effects.

## Data Requirements

- Order-level attribution data or credible maker proxy indicators.
- The same liquid equity or futures instruments used in the queue/refill memo so results can be compared directly.
- Enough depth and event history to estimate cancellation spikes, quote retreat, and regime transitions reliably.

## Known Risks

- Maker identity is often not directly observable, so proxy quality will vary by venue.
- Queue degradation may be confounded with volatility shocks unless the regime classifier controls for concurrent price moves.
- Some venues may show little visible maker dispersion, which weakens maker-count features.

