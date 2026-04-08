---
name: mdream-hypothesis-deepening
description: Run the full mdream hypothesis-discovery loop for surprising trade ideas. Use when you need to explore a research prompt across multiple mdream rounds, reform prompts to escape repeated basins, drill into papers and sections, and converge on a genuinely surprising, testable strategy thesis with first test and gap-to-close.
---

# mdream Hypothesis Deepening

Use this skill when the task is not just "search the corpus" but "keep pushing until the best surviving lead is surprising, distinct, and testable."

This skill assumes `mdream` is on `PATH` and usable globally.

Core commands used by this skill:

- `mdream discover round`
- `mdream paper get`
- `mdream paper sections`
- `mdream surface get`
- `mdream hypothesis add`
- `mdream hypothesis score`
- `mdream hypothesis top`
- `mdream note add`

## Objective

Optimize for the best surviving hypothesis, not the best first retrieval hit or the best retrieval score.

Use this target function:

`deep_candidate_score = surprise + distinctness + executability + evidence_quality - basin_repetition - generic_microstructure_drag`

Operationally:

- `surprise`: the lead is not just queue/refill or generic impact
- `distinctness`: it opens a different mechanism family, lane, or market-state view
- `executability`: it can state a plausible `first_test`, `modern_equivalent`, and `gap_to_close`
- `evidence_quality`: at least one paper-level lead plus either section evidence or a canonical surface support it
- `basin_repetition`: penalize results that keep returning the same paper family without sharpening the thesis
- `generic_microstructure_drag`: penalize results that are true but too generic to matter for immature markets

The CLI now persists a judgment loop for this:

- `discover round` gives retrieval leads and the current `session_objective`
- `hypothesis add` stores a candidate thesis in the session
- `hypothesis score` records the agent's judgment after reading and computes:
  - `surprise_score`
  - `objective_score`
- `hypothesis top` returns the best currently scored session hypotheses

Use the CLI's stored `objective_score` as the live optimization target across rounds.

## Success Condition

Do not stop because the top score is high.

Stop only when you can state all of:

- one-sentence strategy thesis
- why it is surprising
- why it fits thin / immature / weakly arbitraged markets
- the minimum viable first test
- the main gap to close

If you cannot state those five fields, keep digging.

## Standard Loop

### 1. Open a fresh session

Start broad but pointed:

```bash
mdream discover round --new-session --label <short-label> --prompt "<research prompt>" --json
```

Extract from the result:

- `session_id`
- top `items`
- `candidate_diversity`
- `paper_hits`
- `surface_hits`
- `session_objective`

If `session_objective.status = unscored`, the next step is to create and score at least one concrete hypothesis.

### 2. Judge the round

Classify the round immediately:

- `broadening`: useful new lane or mechanism surfaced
- `refining`: same lane, but clearer mechanism or better first test emerged
- `collapsing`: same 2-3 papers or same generic microstructure basin keeps returning

If collapsing, do not repeat the same prompt with different wording.

### 3. Promote one branch, not ten

Take the best branch using these rules:

- prefer a lead that is not generic mature-book microstructure
- prefer a lead with explicit venue, regime, rule, or actor asymmetry
- prefer a lead that changes the action from "quote tighter" to a more specific behavior
- prefer section-backed reasoning over abstract-only familiarity

Then inspect it:

```bash
mdream paper get --paper-id <paper_id> --full --json
mdream paper sections --paper-id <paper_id> --full --json
mdream surface get --surface diamond-board --item-id <publication_item_id> --full --json
```

Use only the commands that apply to that lead type.

### 4. Store a hypothesis before the next branch

Turn the best branch into one explicit thesis:

```bash
mdream hypothesis add --session-id <session_id> --title "<short title>" --text "<one-sentence thesis>" --target-market "<market family>" --json
```

Then score it after reading:

```bash
mdream hypothesis score \
  --hypothesis-id <hypothesis_id> \
  --lead-id <lead_id> \
  --paper-id <paper_id> \
  --result-id <result_id> \
  --prior-novelty <0-10> \
  --posterior-novelty <0-10> \
  --prior-plausibility <0-10> \
  --posterior-plausibility <0-10> \
  --thin-market-fit <0-10> \
  --executability <0-10> \
  --evidence-quality <0-10> \
  --basin-repetition-penalty <0-10> \
  --generic-drag-penalty <0-10> \
  --json
```

After scoring, check the live objective:

```bash
mdream hypothesis top --session-id <session_id> --json
```

The agent should now be steering toward a stored `objective_score`, not only a remembered impression.

### 5. Re-form the hypothesis

Write the next prompt as a branch instruction, not a restatement.

Good follow-up prompt shapes:

- `follow the <mechanism> branch`
- `ignore generic market making`
- `search for trades where <state A> and <state B> diverge`
- `focus on selective non-participation rather than spread capture`
- `find repair timing, not equilibrium pricing`

Each next prompt should do at least one of:

- narrow to one mechanism
- exclude the current basin
- force a different action model
- force a different failure mode

### 6. Run the follow-up round

```bash
mdream --session <session_id> discover round --prompt "<refined prompt>" --json
```

After each follow-up, ask:

- did the top papers materially change?
- did the mechanism get sharper?
- did executability improve?
- did the new evidence improve the best stored `objective_score`?

If no to all three, the branch is stuck.

## Basin Escape Rules

If `mdream` keeps returning the same family:

1. Name the basin explicitly in the next prompt.
2. Exclude it.
3. Force a different action.

Example:

- bad: `focus more on low-volume event markets`
- good: `ignore queue microstructure; find rule-shaped repair timing across linked venues`

Use these escape moves:

- `ignore generic market making`
- `not pure spread capture`
- `not queue/refill unless tied to a new actor or state`
- `search for legal-state vs execution-state divergence`
- `search for should-not-quote windows`
- `search for venue-rule asymmetry`

## Minimum Depth

Default depth is:

- 1 opening round
- hypothesis add + first score
- 2+ follow-up rounds with rescoring

Go deeper if the branch is improving.

Stop at 4-6 rounds unless each round is clearly sharpening the same thesis.

## Required End Product

At the end, report:

- where you started
- each round prompt
- what changed between rounds
- the best stored `objective_score`
- the best stored `surprise_score`
- final surviving hypothesis
- why it is surprising
- first test
- gap to close

If multiple sessions were run, compare them and choose the strongest final thesis.

## Quality Bar

A final idea is strong if it changes one of these:

- action:
  from `trade the spread` to `trade the repair timing`, `stand down`, `wait for re-entry`, `watch collateral release`, etc.
- state:
  from `price is wrong` to `market is in the wrong local state`
- actor:
  from `the crowd trades` to `a small informed subgroup or arbitrageur population causes the edge`
- regime:
  from `always-on microstructure effect` to `only in thin, immature, rule-shaped venues`

## Anti-Patterns

Do not:

- stop after the first good-looking paper
- accept abstract-only familiarity as a finding
- keep rephrasing the same prompt without excluding the current basin
- confuse a retrieval hit with a strategy thesis
- report a lead as surprising if it is just another mature-book market-making variant

## Fast Template

Use this cadence:

1. opening prompt
2. inspect top non-generic branch
3. add a hypothesis
4. score it after reading
5. inspect `hypothesis top`
6. reform prompt to exclude the basin or sharpen the action
7. inspect again
8. rescore if the thesis changed
9. repeat until one branch yields:
   - a distinct mechanism
   - an improving `objective_score`
   - a concrete first test
   - a real gap to close

## Notes

- `discover round` is corpus-first by default. Use `--prefer-surfaces` only if you explicitly want canonical priors to dominate.
- Prefer runtime paper and section evidence first. Use surfaces to validate or sharpen, not to anchor the whole search.
- If a paper only exposes `section_or_abs`, treat it as weaker evidence than real section text.
- `hypothesis top` is the authoritative view of the session's current best judged idea.
- If a new round does not beat the best stored `objective_score`, assume the new branch is weaker unless it opens a genuinely new mechanism family worth a speculative retry.
