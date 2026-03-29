# Auction-to-Continuous Transition Seam

## Hypothesis

Queue value and refill asymmetry immediately after auction uncrossing may carry more execution signal than the same variables later in the continuous session, creating a distinct post-uncrossing quoting regime.

## Supporting Papers

- `2101.03086` (Market Making with Stochastic Liquidity Demand: Simultaneous Order Arrival and Price Change Forecasts)
- `1011.6402` (The Price Impact of Order Book Events)
- `cond-mat/0210475` (Statistical theory of the continuous double auction)

## Venue-Specific State Boundary

- First concrete venue: NYSE opening auction.
- Auction mode ends at the official uncrossing timestamp disseminated by the auction feed.
- Continuous-book mode begins with the first regular-way continuous-book event after the uncrossing print.
- Secondary venue candidate for replication: Euronext closing auction, using the same boundary logic around the official uncrossing event and the first post-auction continuous-book update.

## Uncrossing Window Definition

- Primary definition: the first 10 seconds after the auction price is set.
- Secondary definition for robustness: the first 200 book events after uncrossing.

## Data

- Auction event feeds with official uncrossing timestamps and auction prints.
- Post-auction limit-order-book reconstruction at message or high-resolution snapshot level.
- Enough opening or closing auctions to support matched post-uncrossing and later-session control windows, ideally at least three months on a liquid venue.

## Baseline

A queue-priority-only model estimated on later continuous-session windows, without auction-state boundaries or refill-speed asymmetry.

## Test 1

Does queue priority gained immediately after uncrossing predict short-horizon adverse selection better than queue priority gained 5 minutes later? Measure queue rank at entry, subsequent fill probability, and 1-minute and 5-minute markouts, then compare the post-uncrossing window against a matched later-session control window.

## Test 2

Does refill-speed asymmetry in the post-uncrossing window add signal beyond queue priority alone? Estimate depth recovery speed separately on bid and ask, then test whether a model with both queue rank and refill asymmetry explains fill-quality outcomes better than queue rank by itself.

## Metric

Primary metric is short-horizon fill-quality delta: adverse selection after fill in the uncrossing window minus adverse selection for matched later-session entries. Secondary metric is incremental explanatory value from refill-speed asymmetry beyond queue priority alone.

## Stop/Go

Go if immediate post-uncrossing queue priority is measurably more informative than later queue priority, and if refill-speed asymmetry adds signal beyond queue position. Stop if the edge vanishes after venue-specific normalization or reduces to a one-venue artifact.

## Fail-Fast

- Auction mechanics differ materially across venues, so the state boundary may not transfer cleanly.
- Sample sizes for uncrossing events may be small once filters for liquid, clean events are applied.
- Queue priority after uncrossing may proxy for informational urgency rather than a durable microstructure edge.

