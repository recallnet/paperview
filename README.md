# paperview

Literature search and hypothesis deepening for coding agents, built around
[`mdream`](./mdream/README.md) and a shared paper corpus.

`paperview` exists to solve a specific failure mode: agents can retrieve papers,
but they keep rediscovering the same obvious ideas unless the retrieval surface,
the scoring loop, and the session memory all force them to keep moving toward
something more surprising.

---

## The Agent That Kept Rediscovering Queue Refill

You ask an agent:

> Find a surprising trade strategy for thin, weakly arbitraged prediction
> markets that the papers never fully realized.

Without a real loop, the agent does the same thing every time:

- retrieve familiar market-microstructure papers
- tell you about queue refill, auction handoff, or generic impact
- sound smart
- stop before it has actually found anything new

The problem is not retrieval alone. The problem is that the agent has no durable
objective and no persistent memory of what it already believes.

`paperview` fixes that by combining:

- a section-first paper corpus, not title/abstract-only search
- a CLI (`mdream`) that stores sessions, notes, hypotheses, and result IDs
- a scoring loop where the agent records priors and posteriors after reading
- a persistent objective score so later rounds can beat earlier ones instead of
  just sounding different

The result is a workflow where an agent can start broad, keep rescoring what it
learns, and converge on something that is actually surprising and testable.

## What paperview is for

`paperview` has two layers:

1. `mdream/`
   The user-facing research CLI for agents and humans.
2. corpus pipeline
   The maintainer workflow that builds and refreshes the shared SQLite paper
   database that `mdream` searches.

If you are trying to find a strategy idea, use `mdream`.

If you are trying to add papers, rebuild embeddings, or ship a new corpus
release to the team, use the pipeline docs under [docs](./docs/INDEX.md).

## Agent Workflow

This is the core loop:

```text
1. Start with a hypothesis-shaped prompt
2. Run discovery against the corpus
3. Read the best papers and sections
4. Write down an explicit working hypothesis
5. Score prior vs posterior surprise
6. Keep iterating until a later round beats the current objective
```

In practice:

```bash
$ mdream init --json
$ mdream discover round --prompt "find a surprising strategy for thin prediction markets" --json
$ mdream paper sections --paper-id 2012.12555 --full --json
$ mdream hypothesis add --session-id <session> --title "..." --text "..." --json
$ mdream hypothesis score --hypothesis-id <id> --lead-id <lead> --result-id <result> ... --json
$ mdream hypothesis top --session-id <session> --json
$ mdream --session <session> discover round --prompt "follow the best scored branch and get weirder" --json
```

The important part is not retrieval. It is the loop.

- retrieval gives the agent candidate evidence
- scoring gives the agent a real objective
- session memory keeps the agent from starting over every round

## A Real mdream Session

This is the kind of session the repo is designed for: one human kickoff, then a
coding agent running the loop until the thesis is sharper and more surprising
than what it started with.

### Kickoff

Prompt:

> Find a surprising trade strategy for unprofessionalized low-volume prediction
> markets that would not be obvious from mature-book microstructure alone.

Round 1 returned broad branches:

- venue-shaped delayed parity repair
- settlement / resolution timing
- rule-sensitive toxic-flow filters
- state-graph repair timing

That is good search, but not yet a thesis. So the agent picked one branch and
forced itself to score its beliefs rather than just admire the retrieval.

### Round 2: first concrete hypothesis

Working hypothesis:

> In thin prediction markets, one-sided aggressive flow may create temporary
> should-not-quote windows where selective non-participation outperforms
> continuous quoting.

Evidence read:

- `2012.12555` on imbalance-sensitive market impact in trader agents
- the participant-pathologies surface

First score:

- prior novelty: `4`
- posterior novelty: `8`
- prior plausibility: `5`
- posterior plausibility: `8`
- thin-market fit: `9`
- executability: `8`
- evidence quality: `7`
- basin repetition penalty: `2`
- generic drag penalty: `1`

Stored result:

- `surprise_score = 3.5`
- `objective_score = 6.77`

That is already useful. But it is still too close to generic toxic-flow logic.
The agent needs to deepen it, not publish it.

### Round 3: push deeper into the mechanism

Follow-up prompt:

> Follow the highest-scored hypothesis and sharpen the should-not-quote
> toxic-flow thesis for thin prediction markets.

New papers surfaced:

- `2109.10958` on recurring arbitrageur behavior in Mt. Gox
- `1504.04354` on long memory of order flow

What changed:

- the idea stopped looking like generic “avoid bad flow”
- it started looking like a repeated actor/regime problem
- the likely edge became: detect when a small recurring participant set pushes
  the venue into a toxic burst regime, then step away until the imbalance-memory
  decays

Updated score direction:

- novelty stayed high
- plausibility improved because the mechanism was no longer hand-wavy
- executability improved because the strategy could be tested as a filter, not a
  full market-making stack

### Round 4: try to disprove it by branching away

The agent then forced a competing branch instead of letting the first thesis win
by default:

> Ignore generic toxic flow. Find a more surprising alternative in thin event
> markets around settlement lag, venue rule asymmetry, or linked-state repair.

That branch found:

- settlement / resolution timing seams
- state-graph inconsistency monitors
- venue-shaped delayed parity repair

This mattered because it gave the agent a real comparison set. Now the question
became:

> Is “should-not-quote windows” actually better than the best market-design or
> settlement branch?

### Round 5: the actually surprising insight

The strongest comparison result was not “settlement lag” in the abstract. It was
the interaction between:

- recurring actor bursts
- thin venue participation
- delayed local repair

The final thesis became:

> In low-volume prediction markets, the best exploitable signal may not be price
> dislocation itself. It may be the temporary absence condition created when a
> recurring, one-sided participant burst pushes the venue into a toxic local
> state and the repair is slow because there are too few professional dampers.

That is meaningfully better than the starting point.

It is surprising because:

- it does not say “quote better”
- it does not say “arb the spread”
- it does not say “do queue microstructure on a weaker venue”
- it says the edge may be selective non-participation during predictable local
  regime failures

And it is testable:

- first test: mark windows immediately after one-sided aggressive bursts, then
  compare passive fill quality and adverse selection against an always-on quoting
  baseline
- gap to close: identify a practical proxy for recurring toxic actors or burst
  regimes in the target venue

That is the kind of session `paperview` is built to support.

## Why The Corpus Matters

`paperview` does not treat discovery as title search.

The canonical representation is section-first:

- `surprise_sections`
- `mechanism_sections`
- `regime_sections`
- `all_sections`

That matters because the interesting parts of a paper usually are not in the
title. Surprise tends to live in:

- discussion
- implications
- limitations
- regime conditions
- mechanism paragraphs

If you rank mostly on titles and abstracts, agents drift back toward the same
well-labeled discourse. If you rank on the sections where the paper explains
what really happened and under what assumptions, you get a much better chance of
finding something the paper did not explicitly cash out as a trading idea.

## How mdream Works

`mdream` is the interface agents use.

It provides:

- corpus search
- paper and section drilldown
- stored results with paging and `--full`
- session memory
- notes
- hypothesis tracking
- hypothesis scoring
- top-hypothesis retrieval
- a live session objective that later rounds can target

That means the agent does not need to manage SQLite files or scratch notebooks.
It just uses the CLI and keeps moving.

## Quickstart

1. Fetch the shared corpus bundle so the source DB exists at
   `data/structural-analogy/paperview.sqlite3`
2. Install `mdream`

```bash
./scripts/bootstrap_mdream.sh
```

3. Initialize the local store

```bash
mdream init --json
```

4. Start a real session

```bash
mdream discover round \
  --prompt "find a surprising strategy for unprofessionalized low-volume prediction markets" \
  --json
```

## Repo Layout

- [`mdream/`](./mdream/README.md): CLI source and command surface
- [`corpus/manifest.json`](./corpus/manifest.json): corpus compatibility contract
- [`reports/published/`](./reports/published/): checked-in publication surfaces
- [`docs/operator-guide.md`](./docs/operator-guide.md): how humans and agents
  should run the loop
- [`docs/corpus-build.md`](./docs/corpus-build.md): how maintainers add papers
  and refresh the corpus
- [`docs/corpus-release.md`](./docs/corpus-release.md): how to package and share
  the DB with a team

## What ships in git vs LFS

Keep the split clean:

- git: code, docs, configs, schemas, manifests
- Git LFS or release assets: the large source DB, typically
  `data/structural-analogy/paperview.sqlite3`

`mdream` keeps its local session/history store outside the repo under:

- `~/Library/Application Support/mdream/mdream.sqlite3`

Runtime state should not live in the product tree.
