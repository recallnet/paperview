# Research Memo

There may be executable edge in modeling passive quote value immediately after shocks, auctions, or maker withdrawals, especially when refill timing and queue dynamics diverge from naive displayed-depth assumptions.

## Three Best Practical Leads

### 1. Post-shock passive quoting via queue value plus refill lag

What it is: Passive quote value after a shock appears to depend on both queue priority and liquidity refill lag rather than on spread alone.
Why the system surfaced it: the queue/refill pairing is the only cross-domain idea that survived all the way to publication, and the same motif kept recurring across bridge, composition, and transition-state evidence instead of appearing as a one-off packet.
What papers back it: `1902.10743` (From Glosten-Milgrom to the whole limit order book and applications to financial regulation), `2408.03181` (Correlation emergence in two coupled simulated limit order books), `2406.04969` (An Algebraic Framework for the Modeling of Limit Order Books), `2009.02808` (Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants), `1005.0182` (A Multi Agent Model for the Limit Order Book Dynamics).
First test: Measure queue-position edge after volatility shocks with refill-time controls on recent LOB data.
Gap remaining: The literature isolates queue value and resiliency separately and stops short of an execution rule that combines them. The missing piece is a live rule that ties shock state, queue position, and refill timing into one quoting policy.

### 2. Auction-to-continuous-book transition seam

What it is: Auction price formation may hand off into a temporarily underfilled book where liquidity refill lags price discovery. Queue value appears to change abruptly at the auction-to-continuous transition, suggesting a distinct post-uncrossing quoting regime.
Why the system surfaced it: the auction seam survived twice as a transition-state publication surface and separately as an accepted bridge lead, which means the handoff signal appears both in direct microstructure papers and in cross-domain recombination.
What papers back it: `2101.03086` (Market Making with Stochastic Liquidity Demand: Simultaneous Order Arrival and Price Change Forecasts), `1011.6402` (The Price Impact of Order Book Events), `cond-mat/0210475` (Statistical theory of the continuous double auction).
First test: Measure whether queue priority gained immediately after auction uncrossing predicts short-horizon adverse selection. Then test whether refill-speed asymmetry in the same post-uncrossing window adds incremental signal beyond queue priority alone.
Gap remaining: Need a venue-by-venue definition of the auction-to-book state boundary. The seam still needs a venue-specific definition of when auction logic hands off to continuous-book logic.

### 3. Maker-retreat regime switch for queue-based quoting

What it is: Displayed depth can lose protective value when makers retreat under stress, changing what queue position is worth.
Why the system surfaced it: the accepted bridge says displayed depth stops being reliable protection when makers back away, and the same queue-centric microstructure papers keep reappearing in the near-miss set, which points to a regime switch rather than a generic liquidity story.
What papers back it: `1005.0182` (A Multi Agent Model for the Limit Order Book Dynamics), `2009.02808` (Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants), `2101.03086` (Market Making with Stochastic Liquidity Demand: Simultaneous Order Arrival and Price Change Forecasts).
First test: Backtest queue survival and fill quality when maker inventory stress indicators spike.
Gap remaining: the lead still lacks a dedicated transition-state ledger entry, so the maker-withdrawal regime has an accepted interpretation but not yet a publication-grade representative seam or canonical representative paper.

## The Stranded Results That Came Back

### 1. 2106.00581 — $N$-player and Mean-field Games in Itô-diffusion Markets with Competitive or Homophilous Interaction (2021-06-14)

What it is in plain language: The paper offers a concrete illiquidity-aware execution control that still looks testable on modern data.
What changed since publication: modern depth feeds, cheaper intraday calibration, and queue-aware backtesting infrastructure make an impact-aware control law much easier to test now than it was in 2021.
Why it matters now: the old result reads like math-finance control theory, but today it can be treated as a concrete adaptive execution policy for fragmented electronic books. Modern equivalent: adaptive execution with impact-aware control
First test: Re-estimate the proposed impact-aware control on current intraday data and compare it to simpler adaptive execution baselines.
Gap remaining: Need evidence that the control law survives modern queue dynamics and hidden-liquidity behavior.

### 2. 2204.08581 — On Parametric Optimal Execution and Machine Learning Surrogates (2023-10-29)

What it is in plain language: Machine-learning surrogates can speed the search for near-optimal execution schedules under parametric impact models.
What changed since publication: surrogate-model tooling, GPU inference, and broader venue-fragmented execution data make fast policy search much more operationally plausible now than when the paper first appeared.
Why it matters now: the original result sat inside calibration language, but today it looks like a practical execution-research workflow for searching policy space quickly. Modern equivalent: execution policy search with fast surrogates
First test: Replicate the surrogate-assisted execution policy on newer fragmented limit-order-book data with realistic fees.
Gap remaining: Need to show that the surrogate remains stable under venue fragmentation and regime shifts.

## The Transition-State Seam Map

- queue x refill: evidenced. Passive quote value after a shock appears to depend on both queue priority and liquidity refill lag rather than on spread alone. This seam has the strongest support because it is already a published cross-domain idea and keeps reappearing in the near-miss set.
- auction x refill: evidenced. Liquidity refill after auction uncrossing may lag the new price enough to create a brief execution edge. The seam is grounded by `1011.6402` (The Price Impact of Order Book Events) and the accepted auction/refill bridge.
- auction x queue: evidenced. Queue value appears to change abruptly at the auction-to-continuous transition, suggesting a distinct post-uncrossing quoting regime. The seam is grounded by `2101.03086` (Market Making with Stochastic Liquidity Demand: Simultaneous Order Arrival and Price Change Forecasts) and reinforced by the older auction microstructure backdrop in `cond-mat/0210475` (Statistical theory of the continuous double auction).
- maker-stress x queue: provisional evidence. Displayed depth can lose protective value when makers retreat under stress, changing what queue position is worth. It has an accepted interpretation but not yet a dedicated ledger entry.
- parity x refill: speculative. The seam still shows up in transition and bridge evidence, but the current run preserves it only as a rejection (`invalid_enum:classification:BAD_CLASS`) plus the recurring near miss around `1011.6402` (The Price Impact of Order Book Events).

## The Conversion Funnel

The system is strong at discovery and weak at synthesis.

The search started with 17,323 scored discovery papers, narrowed to 24 shortlist items, then to 8 accepted interpretations, and finally to 1 published unrealized cross-domain idea, 2 stranded q-fin results, and 2 transition-state entries.
What this means: discovery is working. The system is repeatedly finding the same microstructure motif across bridge, composition, transition, and stranded-q-fin paths. What is still weak is synthesis and ledger translation: too many good packets stop at interpretation or remain one step away from a publishable test memo.

## What To Do Next

Operationalize the queue x refill seam first. Use full-depth order-book data with event markers for volatility shocks, auction uncrossings, fill outcomes, queue position, refill timing, and maker-withdrawal proxies.
The first test should be an event study plus simulated passive quoting policy: compare a shock-conditioned queue/refill model against naive spread-based passive posting after shocks and immediately after auction uncrossings.
Success means the seam survives realistic fees and adverse-selection controls: the queue/refill-conditioned policy should improve fill-quality-adjusted expectancy, not just fill rate, across more than one venue or instrument.
The second test should layer maker withdrawal on top of the same framework. If queue value degrades materially when makers retreat, that turns the current accepted maker bridge into a concrete regime switch rather than a narrative add-on.

## The Near-Misses That Matter

- `2009.02808` (Limit Order Book (LOB) shape modeling in presence of heterogeneously informed market participants) is worth a second look because it keeps surfacing as the top queue/refill near miss and may supply the state variables for shock-conditioned passive quoting.
- `cond-mat/0210475` (Statistical theory of the continuous double auction) is worth a second look because it is the cleanest older foundation for the auction-to-book transition seam and keeps reappearing around auction/refill evidence.
- `1005.0182` (A Multi Agent Model for the Limit Order Book Dynamics) is worth a second look because it gives a maker-behavior and queue-dynamics lens on why displayed depth may lose protective value under stress.
- `2205.14699` (Managing Risk in DeFi Portfolios) is an interesting cross-domain signal because DeFi settlement and liquidation risk may rhyme with fragmented execution stress even though the venue structure is different.
- `2012.13230` (SoK: Lending Pools in Decentralized Finance) is an interesting cross-domain signal because pool depletion and refill mechanics may transfer into how the system thinks about liquidity recovery after stress.
