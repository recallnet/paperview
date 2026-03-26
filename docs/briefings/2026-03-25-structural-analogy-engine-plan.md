---
doc_type: briefing
owner: devrel
review_policy: periodic-7
reviewed: 2026-03-26
status: active
summary: Living plan and tracker for building a local-first structural analogy engine for strategy discovery from the literature corpus.
tags:
  - docs
  - briefing
  - research
  - strategy-discovery
written: 2026-03-25
---

# Structural Analogy Engine for Strategy Discovery

## Status

- Overall status: `active`
- Current phase: `phase-3-local-extraction-pipeline`
- Owner: `unassigned`
- Last updated: `2026-03-26`
- Working mode: `local-first`

## Current Focus

- Finish the `q-fin` PDF pull and verify corpus completeness.
- Use repo-native launch/status commands for the corpus pull rather than ad hoc shell commands.
- Materialize a completeness inventory so missing IDs are explicit rather than inferred.
- Keep corpus status and completeness inventory synchronized automatically during the live pull.
- Classify permanent no-PDF cases explicitly so corpus gaps are not mistaken for transient downloader instability.
- Normalize failure artifacts into a canonical latest-per-ID view so evolving downloader behavior does not leave contradictory state behind.
- Distinguish retryable server-side failures from permanent no-PDF failures so later retry policy can be targeted.
- Provide a repo-native requeue path for retryable failures instead of relying on manual ID extraction.
- Provide an automated post-pass retry pipeline so Phase 0 does not end with manual retry orchestration.
- Provide a single readiness-report artifact so Phase 0 can be reviewed and closed explicitly.
- Lock the v1 extraction schema and structural fingerprint ontology.
- Make the checked-in schema files the source of truth for Phase 1 rather than the draft examples in this doc.
- Choose and initialize the canonical local write store for the pipeline.
- Populate the canonical `papers` table from harvested metadata so later phases can build on the local store instead of raw JSONL.
- Materialize a deterministic abstract-first pilot batch from the local store.
- Create prompt-ready abstract extraction runs from the pilot batch before local model execution is locked.
- Ingest validated extraction responses into SQLite so the first pilot can produce real staged rows and canonical `mechanism_instances`.
- Use a concrete local runtime for the first abstract-extraction pass and evaluate whether schema-valid outputs are actually useful.
- Tighten prompt quality until outputs are economically sensible, not just structurally valid JSON.
- Add a repeatable quality gate before widening from smoke tests to pilot-batch execution.
- Make the quality gate operational by distinguishing blocking failures from warning-only findings and enforcing gate-before-ingest behavior.
- Use prompt iteration plus the quality gate to get the known-bad generic-model case below the rollout threshold.
- Make the quality gate schema-aware so unsupported enum labels are treated as blocking extraction failures, not silently counted as parse-ok rows.
- Measure a small real slice under the v3 prompt before attempting the full 200-paper pilot batch.
- Run prompt/schema-alignment iterations against the same 10-paper slice until the schema-aware blocking count materially drops.
- Use targeted smoke tests to eliminate specific blocker classes before spending another full 10-paper benchmark run.
- Promote prompt versions only when the fixed 10-paper benchmark shows a real blocker-count reduction under the schema-aware gate.
- Use targeted smoke tests to retire the last remaining blocker before attempting a zero-blocker rerun of the fixed benchmark slice.
- Promote the active prompt only after the fixed 10-paper benchmark clears fully under the schema-aware gate.
- Use the next wider slice to identify the first blocker classes that reappear outside the benchmark before attempting ingest beyond the benchmark set.
- Retire wider-slice blocker classes one by one in targeted smoke tests before rerunning the wider slice.
- Re-run the wider slice only after each currently known blocker class has passed in targeted smoke-test form.
- Regenerate widened benchmark slices from the prompt file itself instead of copying old `requests.jsonl` artifacts forward.
- Reduce the widened `25`-paper slice from `1/25` blocking to `0/25` before attempting ingest beyond the fixed benchmark set.
- Use targeted smoke tests to retire the last widened-slice blocker before spending another full `25`-paper rerun.
- Keep targeted smoke-test prompt variants separate from the active batch prompt until they survive the full widened rerun.
- Build the next widened-rerun candidate by merging narrow blocker fixes back into the strongest batch-stable prompt surface.
- Promote the active widened-slice prompt only after the full `25`-paper slice clears under the schema-aware gate.
- Use gate-and-ingest on the first clean widened slice before scaling to larger pilot batches.
- Use the first larger pilot slice as a blocker-discovery pass before any further ingestion.
- Retire larger-slice blocker classes one by one in targeted smoke-test form before spending another full `50`-paper rerun.
- Retire the remaining `50`-paper v18 schema drifts one by one in targeted smoke-test form before another larger-batch verification pass.
- Re-run the `50`-paper verification slice with the current blocker fixes merged into the active batch prompt line.
- Retire the last remaining `50`-paper blocker before the first larger gate-and-ingest attempt.
- Re-run the full `50`-paper slice with the final `why_missed` fix merged into the batch prompt line.
- Keep targeted `why_missed` fixes separate from the active larger-batch prompt until they survive a full `50`-paper rerun.
- Prefer narrow exemplar-based `why_missed` fixes over broad global rules when stabilizing the larger-batch prompt line.
- Re-run the full `50`-paper slice with the narrower `v24` merge candidate and check whether the FX fix survives without the `v23` overreach regression.
- Narrow the remaining larger-batch failures to specific `high_fit_without_specific_why_missed` cases before the first `50`-paper gate-and-ingest attempt.
- Retire the remaining off-domain larger-batch blockers by forcing political-science measurement and AI ethics / moral-agent papers to stay low-fit and low-portability.
- Build the smallest useful pilot before scaling to full-text processing.

## Progress Board

| Workstream | Status | Notes |
| --- | --- | --- |
| Corpus harvest | `in_progress` | Full metadata complete; repo-native launch/status/inventory commands now exist. `corpus:status` auto-refreshes inventory when the manifest advances, 404 PDF misses are classified as permanent failures, retryable `5xx` failures are classified separately, failure logs are reconciled into a canonical latest-per-ID view, retryable IDs can be re-queued from the canonical inventory, a pipeline runner automates the post-pass retry step, and a readiness report artifact now summarizes Phase 0 state while the live pull continues. |
| Schema design | `in_progress` | V1 extraction and fingerprint schema artifacts now live under `schemas/` and validate against bundled examples; SQLite is now the canonical v1 write store, the `papers` table can be populated from harvested metadata, adjacent corpora can now be stamped with `literature_family` and `evaluation_split`, and enum hardening remains open. |
| PDF extraction | `in_progress` | A repo-native section parser now uses downloaded PDFs to populate `paper_sections`, logs unreadable or missing files into `parse_failures`, and upgrades canonical evidence spans to section-backed snippets when parsed text supports the mechanism summary. |
| Structured extraction | `in_progress` | A deterministic abstract-first pilot batch can now be materialized from the SQLite store, prompt-ready abstract extraction runs can be registered and exported, validated responses can be ingested into a transitional `paper_extractions` buffer, and the first local MLX backend has completed smoke tests. The quality-review gate now distinguishes `blocking` vs `warning` findings, validates outputs against `schemas/extraction.schema.json`, and a repo-native gate-and-ingest command enforces the policy before persistence. The active extraction contract now also requires `insight_type`, `required_assumptions`, `assumption_violations`, `fragility_flags`, `capacity_constraints`, `failure_regimes`, and `negative_transfer_rationale`, and the reviewer blocks promising candidates that lack specific blocker context. Prompt v3 clears the known-bad generic-model smoke test, but the first 10-paper slice shows `5` blocking schema-normalization failures after schema-aware review. Prompt v4 improves some field mappings on the same slice, but the blocking count remains `5/10`. Prompt v5 fixes the off-domain `math.OC` / logistics optimization failure mode and reduces the fixed 10-paper benchmark from `5/10` blocking to `1/10` blocking. Prompt v6 resolves the last remaining benchmark blocker and clears the fixed 10-paper benchmark at `0/10` blocking. On the first wider `25`-paper slice, v6 yields `2/25` blocking (`8%`). Prompt v7 retires the numerical American-option solver blocker in targeted smoke-test form, and prompt v8 retires the generic credit-risk ML blocker in targeted smoke-test form. The widened-slice rerun is now generated directly from the prompt file via `create_extraction_run.py --max-requests` rather than copied request artifacts, and the first valid v8 `25`-paper rerun improves the slice to `1/25` blocking (`4%`). Prompt v9 retires the final known widened-slice blocker in targeted smoke-test form for `2412.03618`, but the full v9 `25`-paper rerun regresses to `20/25` blocking because many rows drop required fields like `mechanism_name`. Prompt v10 merges the `2412.03618` fix back into the stronger v8 surface, passes the targeted smoke test cleanly, and clears the full widened `25`-paper slice at `0/25` blocking. The first beyond-benchmark gate-and-ingest pass has now succeeded on that v10 slice, inserting `25` clean rows into the staged store and marking the run `ingested`. The first larger `50`-paper v10 review slice does not stay clean: it lands at `3` blocking and `1` warning, so larger-scale extraction needs another blocker-retirement loop before ingestion. Prompt v12 retires the first of those new larger-slice blocker classes in targeted smoke-test form: `2510.07444` no longer emits invalid `debt` or `loan` labels and passes cleanly. Prompt v13 retires the second larger-slice blocker class in targeted smoke-test form: `2210.15329` no longer emits a pipe-joined multi-domain label, preserves required mechanism fields, and passes the schema-aware gate. Prompt v14 retires the third larger-slice blocker class in targeted smoke-test form: `2511.17963` no longer emits invalid `trend_following`, collapses to low-fit `other` output, and passes the schema-aware gate cleanly. But the first full v14 `50`-paper verification rerun is still not clean: it lands at `4/50` blocking and `0` warning, with three rows dropping `mechanism_name` under conservative collapse and one regression back to invalid `debt` / `loan` output on `2510.07444`. Prompt v15 fixes that `2510.07444` regression again in targeted smoke-test form by explicitly collapsing debt/loan VaR papers all the way to `other` across edge, execution, conditions, and failure fields. Prompt v16 fixes the missing-required-key conservative-collapse class in targeted smoke-test form across `2205.01524`, `cond-mat/0012514`, and `cond-mat/0108452`. The reviewer now treats placeholder names like `mechanism_name = "None"` as blocking, and prompt v18 resolves that representative placeholder-name generation failure in targeted smoke-test form for `cond-mat/0108452` by producing a concrete title-derived mechanism name. The first full v18 `50`-paper verification rerun materially improves the larger-batch surface to `2/50` blocking and `1/50` warning. Prompt v19 now retires the `2206.05410` market-making schema drift in targeted smoke-test form by keeping `inventory_pressure` in `edge_source` and out of `required_market_conditions`. Prompt v21 now retires the `2103.11557` unsupported-domain drift in targeted smoke-test form by collapsing venture-capital exit-timing papers cleanly to low-fit `other` output. The warning-only `2311.02434` DeFi drift turned out to be a reviewer-keyword issue rather than a prompt failure; after broadening the reviewer’s explicit DeFi cues, the refreshed `v18` quality report drops to `2/50` blocking and `0/50` warning. Prompt v22 merges the current prompt-side fixes back into the active `v18` batch line and improves the full `50`-paper rerun to `1/50` blocking and `0/50` warning. Prompt v23 retires the last blocker in targeted smoke-test form for `2002.02583` by forcing high-fit FX/linked-market papers to use specific `why_missed` reasons such as `buried_in_non_prediction_market_language` and `requires_linked_market_modeling`. But the full `v23` `50`-paper rerun regresses badly to `9/50` blocking: the new `why_missed` rule causes broad high-fit / high-portability overreach and an invalid `Q_learning` execution label to reappear. Prompt v23 should therefore remain a targeted branch only, not the new active batch prompt. Prompt v24 now keeps the targeted FX exemplar from `v23` but drops the broad global high-fit rule, and it resolves `2002.02583` cleanly in targeted smoke-test form. The full `v24` `50`-paper rerun materially improves on `v23` but still does not clear: it lands at `4/50` blocking and `0/50` warning. Prompt v25 now retires the two remaining off-domain overreach papers (`2301.11084` and `2305.11519`) in targeted smoke-test form by forcing political-science measurement and AI ethics / moral-agent papers to stay low-fit and low-portability. The remaining unresolved `v24` blocker set is now narrowed to the genuinely market-adjacent high-fit cases, primarily `2206.05410` and `1310.6873`, that still need specific `why_missed` reasons. The active ingest path now also accepts a paper-level `mechanism_instances` batch format, promotes accepted rows into canonical `mechanism_instances` plus `mechanism_evidence_spans`, and ships a backfill script for older valid staging rows. A checked-in mixed-family pilot definition and `v26` wrapper-style prompt now exist, and the quality gate reports Gate A rollout metrics such as `semantic_pass_rate`, `unsupported_enum_ratio`, and blocker-plus-evidence coverage on mixed-family wrapper outputs. Full-text preparation can now upgrade evidence spans from abstract fallback to actual parsed section snippets without changing the mechanism-first storage model. |
| Fingerprint ontology | `in_progress` | The active fingerprint contract now maps accepted mechanism instances into mechanism-level normalized facets plus deterministic `fingerprint_text`, and ambiguous mappings are queued in `normalization_reviews`; broader retrieval-side calibration remains open. |
| Discovery benchmark | `in_progress` | A checked-in retrieval benchmark definition now exists with adjudicated lexical/structural buckets, explicit baselines, and materialization into `benchmark_pairs`; the retrieval stack itself is not built yet. |
| Embeddings + graph | `planned` | Not started. |
| Candidate scoring | `planned` | Not started. |
| Human review queue | `planned` | Not started. |

## Open Questions

- How wide should the first adjacent-domain expansion be beyond `q-fin`?
- What is the minimum evidence bar for a strategy candidate to enter the review queue?

## Decision Log

| Date | Decision | Why |
| --- | --- | --- |
| 2026-03-25 | Make the system local-first. | Keeps iteration cheap and private; remote inference is fallback only. |
| 2026-03-25 | Optimize for structural analogy, not plain semantic similarity. | The goal is to find non-obvious transferable mechanisms. |
| 2026-03-25 | Treat `q-fin` as the anchor corpus, not the whole universe. | Direct neighbors are too obvious for the target use case. |
| 2026-03-26 | Use `scripts/corpus_status.py` as the canonical Phase 0 readiness check. | Corpus progress and downloader health need a single repo-native status surface. |
| 2026-03-26 | Use `scripts/launch_qfin_download.py` and `npm run corpus:launch` as the canonical downloader start path. | The previous background launch died silently; Phase 0 needs a repeatable repo-managed restart flow. |
| 2026-03-26 | Use `scripts/corpus_inventory.py` and `npm run corpus:inventory` as the canonical completeness inventory path. | Phase 0 needs exact missing/downloaded/failed sets, not just aggregate counters. |
| 2026-03-26 | Treat `npm run corpus:status` as the sync point for both liveness and completeness. | Operator workflow is simpler if status auto-refreshes stale inventory instead of requiring a separate manual inventory refresh. |
| 2026-03-26 | Treat PDF `404` responses as permanent no-PDF failures. | Some old-style arXiv IDs have abstract pages but no downloadable PDF; retrying those as transient failures wastes time and obscures real progress. |
| 2026-03-26 | Canonicalize failures as latest-per-ID records in inventory artifacts. | Downloader behavior changed mid-run, so raw failure logs can contain duplicate or obsolete entries that should not pollute corpus state. |
| 2026-03-26 | Treat exhausted HTTP `5xx` failures as explicitly retryable server-side failures. | Server-side errors are operationally different from permanent no-PDF cases and should remain separable for later retry policy. |
| 2026-03-26 | Use a canonical retry queue derived from reconciled failures. | Operators should not have to hand-build retry ID files; retryable failures should flow from the inventory artifacts. |
| 2026-03-26 | Provide a pipeline runner for main-pass download plus bounded retry passes. | Phase 0 should not depend on someone manually chaining downloader, inventory, and retry commands after the main pass completes. |
| 2026-03-26 | Use `corpus:readiness` as the canonical Phase 0 review artifact. | Phase 0 should end with a concrete report, not just a collection of operational commands. |
| 2026-03-26 | Use checked-in JSON schema files under `schemas/` as the Phase 1 contract surface. | The extraction pipeline needs a concrete, versionable target before prompt work and normalization code start. |
| 2026-03-26 | Use SQLite as the canonical v1 write store, with DuckDB deferred only if SQLite later proves insufficient for read-side analytics. | The pilot needs a zero-dependency transactional local store more than it needs a richer analytical engine, and local `sqlite-vec` availability keeps the first vector path SQLite-native longer. |
| 2026-03-26 | Use the SQLite `papers` table as the canonical metadata surface for the pilot. | Later phases should read from the local store rather than repeatedly reparsing raw corpus JSONL files. |
| 2026-03-26 | Use a deterministic stratified 200-paper pilot batch with a downloaded-PDF quota for the abstract-first pilot. | Early extraction work needs a reproducible and reasonably diverse batch that still keeps some papers ready for later full-text follow-up. |
| 2026-03-26 | Split abstract extraction into a run-preparation layer before model execution. | The local model stack is still open, but the repo can still lock prompt versioning, run IDs, and request artifacts now. |
| 2026-03-26 | Validate extraction responses at ingestion time and persist only schema-valid rows. | The pilot needs fast feedback on model quality without polluting `paper_extractions` with malformed outputs. |
| 2026-03-26 | Use `mlx-lm` with `mlx-community/Qwen2.5-3B-Instruct-4bit` as the first local abstract-extraction backend on this machine. | `ollama`, `vllm`, and `llama.cpp` were unavailable locally, while this Apple M4 Max machine can run MLX locally without system-level installation work. |
| 2026-03-26 | Add a stricter abstract extraction prompt variant before running the full pilot batch. | The first MLX sample was schema-valid but economically nonsensical, so prompt quality had to improve before scaling out. |
| 2026-03-26 | Add a heuristic quality-review gate before widening extraction runs. | Schema validation alone is too weak; the pilot needs an explicit way to catch semantically implausible outputs before batch execution. |
| 2026-03-26 | Treat semantic overreach on generic model papers as a blocking extraction failure, not a warning. | Overconfident portability/fit/domain claims are dangerous enough that batch rollout should stop when they appear. |
| 2026-03-26 | Require gate-before-ingest for extraction runs once the quality gate is available. | Review policy is not useful if blocked outputs can still be ingested through the default workflow. |
| 2026-03-26 | Use a few-shot prompt variant for abstract extraction quality work. | Rule-only prompting reduced some failures, but the known-bad generic-model case did not pass until the prompt included explicit positive and negative examples. |
| 2026-03-26 | Make the extraction quality gate schema-aware and treat unsupported enum labels as blocking failures. | The first 10-paper v3 slice looked mostly clean under heuristic review, but schema-aware review showed normalization errors were still common enough to block rollout. |
| 2026-03-26 | Benchmark prompt/schema iterations against the same fixed 10-paper slice before widening the batch. | Quality work needs a stable comparison set; otherwise prompt changes and paper mix are confounded. |
| 2026-03-26 | Use targeted one-paper smoke tests to retire specific blocker classes before rerunning the full 10-paper benchmark. | Full-slice reruns are more expensive and noisier; specific failure modes should be fixed and verified locally first. |
| 2026-03-26 | Treat prompt v5 as the current leading extraction prompt because it is the first version to materially reduce fixed-slice blocking under schema-aware review. | The fixed 10-paper benchmark dropped from `5/10` blocking to `1/10` blocking under v5, which is the first real batch-level quality gain. |
| 2026-03-26 | Require the final blocker class to pass in targeted smoke-test form before attempting a zero-blocker fixed-slice rerun. | This keeps the last benchmark rerun focused on verification rather than discovery. |
| 2026-03-26 | Promote prompt v6 as the active Phase 3 extraction prompt because it is the first version to clear the fixed 10-paper benchmark under the schema-aware gate. | The fixed benchmark now passes at `0/10` blocking under v6, which is the first fully gate-clean prompt version. |
| 2026-03-26 | Use the first wider `25`-paper slice as the next quality gate after the fixed benchmark. | It is large enough to expose new blocker classes without paying the cost of a full `200`-paper rollout. |
| 2026-03-26 | Retire wider-slice blocker classes with targeted smoke tests before rerunning the wider slice. | This keeps wider-slice reruns focused on verification rather than discovering multiple new issues at once. |
| 2026-03-26 | Re-run the wider slice only after the currently known blocker classes have passed targeted smoke tests. | This keeps the next wider-slice rerun interpretable as a verification step rather than another mixed diagnosis step. |
| 2026-03-26 | Keep targeted smoke-test prompt variants separate from the active batch prompt until they survive the full widened rerun. | Prompt v9 fixed the last known blocker in isolation but regressed the full `25`-paper slice badly by dropping required fields across many rows. |
| 2026-03-26 | Build widened-rerun candidates by merging narrow blocker fixes back into the strongest batch-stable prompt line. | Starting from the strongest batch prompt avoids promoting a targeted branch like v9 that solved one blocker but destabilized the rest of the slice. |
| 2026-03-26 | Promote prompt v10 as the active widened-slice prompt. | It preserves the v8 batch surface, retires the `2412.03618` blocker, and clears the full `25`-paper slice at `0/25` blocking under the schema-aware gate. |
| 2026-03-26 | Treat the clean v10 widened slice as sufficient for the first gate-and-ingest pass beyond the benchmark set. | The `25`-paper v10 slice is the first beyond-benchmark batch to clear the schema-aware gate at `0/25` blocking, so deferring ingestion would no longer buy signal. |
| 2026-03-26 | Treat the first `50`-paper v10 run as a blocker-discovery pass, not an ingest candidate. | The larger slice surfaced three new blocking classes and one warning, so it is still better used as a diagnosis set than as a persistence candidate. |
| 2026-03-26 | Retire the larger-slice blocker classes one at a time in targeted smoke tests before rerunning the full `50`-paper slice. | The first larger batch exposed a small number of concrete new failure classes, so it is cheaper and clearer to eliminate them locally first and use the next full rerun as a verification pass. |
| 2026-03-26 | Regenerate widened benchmark slices from the prompt file with `create_extraction_run.py --max-requests` instead of copying old request artifacts. | Copied `requests.jsonl` files preserve stale embedded prompt text and make prompt-version comparisons invalid even when the run metadata changes. |
| 2026-03-26 | Retire the final widened-slice blocker in targeted smoke-test form before spending another full `25`-paper rerun. | The last blocker is narrow and deterministic enough that it is cheaper to fix locally first, then use the next wider-slice run as a clean verification pass. |
| 2026-03-26 | Treat missing required descriptive fields on conservative outputs as a blocker-class regression, not an acceptable side effect of collapse-to-`other` prompting. | The first `2210.15329` smoke fixed the enum drift but dropped `mechanism_name`; targeted blocker fixes still need to preserve the full extraction contract. |
| 2026-03-26 | Treat generic forecasting-plus-RL portfolio optimization papers as low-fit `other` outputs unless they describe a concrete execution mechanism. | The last `50`-paper blocker class came from a model inventing `trend_following` and medium fit on a generic multi-asset allocation paper, which is not close enough to `tradecore` to justify a transferable-mechanism label. |
| 2026-03-26 | Do not promote the merged larger-batch prompt line until it survives the full `50`-paper verification rerun without reviving previously retired blockers. | The first full v14 rerun reintroduced the `2510.07444` debt/loan failure and produced three missing-`mechanism_name` collapses, so targeted smoke-test success is still not enough to trust the merged batch prompt. |
| 2026-03-26 | Force generic debt/loan portfolio VaR papers to collapse all the way to `other` across edge, execution, market conditions, and failure fields. | In the merged batch line, leaving those fields implicit let the model re-infer invalid `debt`, `loan`, and execution-like labels even though `tradecore_fit` stayed low. |
| 2026-03-26 | Treat missing `mechanism_name` / `mechanism_summary` on conservative-collapse outputs as a generic prompt-contract bug class, not a paper-specific issue. | The three remaining blockers in the `50`-paper rerun are structurally the same failure: the model collapses to all-`other` correctly but drops required descriptive fields. |
| 2026-03-26 | Placeholder values like `mechanism_name = "None"` are not acceptable just because they pass schema validation. | The v16 cond-mat smoke resolved the missing-key failures, but one output still used a semantically empty placeholder name, which should be treated as a quality problem before batch promotion. |
| 2026-03-26 | Block placeholder mechanism names in the reviewer before trusting another larger-batch rerun. | Schema validation cannot catch semantically empty names like `None`, and the v16 cond-mat smoke showed that this failure mode is real enough to pollute a batch if the reviewer stays silent. |
| 2026-03-26 | Use explicit title-derived naming examples for statistical-scaling / time-series characterization papers. | Simply forbidding placeholder names in the prompt was not enough for `cond-mat/0108452`; the model needed a concrete pattern for deriving a neutral mechanism name from the paper title/topic. |
| 2026-03-26 | Treat the full `50`-paper v18 rerun as the new larger-batch baseline. | It removes the earlier debt and missing-name failures and leaves a much smaller, cleaner blocker set than the v14 verification run. |
| 2026-03-26 | Keep `inventory_pressure` and `queue_position_value` in `edge_source`, not `required_market_conditions`, for market-making papers. | The `2206.05410` blocker in the v18 `50`-paper baseline came from the model putting an allowed edge label into a disallowed conditions field, so the prompt contract now needs to separate mechanism source from market-structure conditions explicitly. |
| 2026-03-26 | Collapse venture-capital exit-timing papers to `original_market_domain = other` unless the abstract describes a concrete tradable execution mechanism. | The `2103.11557` blocker in the v18 `50`-paper baseline was a pure unsupported-domain drift; the model was already conservative on fit and portability, but still copied `venture_capital` into an enum-limited field. |
| 2026-03-26 | Treat explicit DeFi / DAO / blockchain papers as supported `decentralized_finance` cases in the reviewer. | The `2311.02434` warning in the v18 `50`-paper baseline was caused by reviewer keyword drift, not by a prompt or schema problem; explicitly DeFi papers should not be flagged as unsupported domain assignments. |
| 2026-03-26 | Use prompt v22 as the current leading larger-batch candidate while keeping it below promotion until the final `50`-paper blocker is retired. | The merged `v18` + `v19` + `v21` prompt line materially improves the full `50`-paper rerun to `1/50` blocking and `0/50` warning, which is the strongest larger-batch result so far but not yet fully gate-clean. |
| 2026-03-26 | Require specific `why_missed` reasons whenever a paper is labeled `tradecore_fit = high`. | The last `v22` blocker was no longer about schema drift or unsupported domains; it was a logic-quality failure where the model recognized a high-fit linked-market mechanism but still left `why_missed = ["other"]`, which makes the ranking output too weak to trust. |
| 2026-03-26 | Keep targeted `why_missed` prompt fixes separate from the active larger-batch prompt until they survive a full `50`-paper rerun. | Prompt v23 fixed the last blocker in a one-paper smoke test, but the full `50`-paper rerun regressed sharply by turning several generic papers into overconfident high-fit candidates and reintroducing an invalid `Q_learning` execution label. |
| 2026-03-26 | Prefer narrow exemplar-based `why_missed` fixes over broad global high-fit rules when stabilizing the larger-batch prompt line. | Prompt v24 preserves the targeted `2002.02583` fix from `v23` while removing the global rule that appears to have driven the wider high-fit overreach regression. |
| 2026-03-26 | Treat the `v24` full rerun as a partial recovery, not a promotion. | It confirms that the broader v23 overreach came from the global high-fit rule, but the larger batch still has four blocking cases and therefore is not yet ready for the first `50`-paper gate-and-ingest attempt. |
| 2026-03-26 | Treat political-science measurement and AI ethics / moral-agent papers as explicitly off-domain for Phase 3 extraction. | These papers were still drifting into `tradecore_fit = high` and `novel_market_portability = high` despite already collapsed enum fields; they should stay low-fit, low-portability all-`other` outputs. |

## Working Notes

- Use this section as a running scratchpad for implementation notes, dead ends, and observations.
- Prefer appending dated bullets rather than rewriting history.

### 2026-03-25

- Full `q-fin` metadata harvest completed locally.
- Background PDF pull is running under `logs/qfin_download.log`.

### 2026-03-26

- Added `scripts/corpus_status.py` to report expected/downloaded/failure counts plus downloader PID and recent log context.
- Phase 0 now has a canonical status command: `python3 scripts/corpus_status.py`.
- Status check shows the background downloader is no longer running and stalled after 4 PDFs.
- Added `scripts/launch_qfin_download.py` plus `npm run corpus:launch` / `npm run corpus:status` as repo-native operational commands.
- Relaunched the downloader via the launcher; corpus status now shows the process running and download count increasing again.
- Added `scripts/corpus_inventory.py` plus `npm run corpus:inventory` to materialize exact expected/downloaded/missing/failed ID sets.
- Inventory now writes `data/arxiv-qfin/inventory/summary.json` and the corresponding ID lists for reconciliation.
- Updated `scripts/corpus_status.py` to auto-refresh the inventory snapshot when the manifest advances, so status and completeness stay aligned during the live pull.
- Confirmed a real old-style edge case: `cond-mat/0012479` has an abstract page but no PDF endpoint.
- Updated the downloader to classify PDF `404` as a permanent failure and restarted the live pull so the new logic is active.
- Added `scripts/reconcile_failures.py` and wired it into `scripts/corpus_inventory.py` so failure artifacts are normalized to the latest record per paper ID.
- Canonical failure summary now records duplicate rows removed and failure-type counts.
- Updated the downloader to classify exhausted HTTP `5xx` failures as `retryable_http_5xx` instead of generic unknown failures.
- Confirmed with a focused repro that `math/0309211` now lands as a retryable server-side failure after retries exhaust.
- Added `scripts/retry_failures.py` plus `npm run corpus:retryable-failures` to materialize the retryable failure queue from canonical failure artifacts.
- Confirmed the retry driver can run a focused retry pass against the canonical retryable set without hand-editing IDs.
- Added `scripts/run_qfin_pipeline.py` plus `npm run corpus:run-pipeline` / `npm run corpus:launch:pipeline` to automate the main pass + bounded retryable-failure flow.
- Fixed the pipeline to keep inventory and retry artifacts inside the selected corpus data directory instead of leaking into the canonical main corpus during scratch runs.
- Verified the pipeline end to end against an isolated scratch corpus containing one permanent failure and one retryable `5xx` failure.
- Added `scripts/corpus_readiness_report.py` plus `npm run corpus:readiness` to materialize a single JSON/Markdown Phase 0 readiness report.
- Generated the first readiness artifact under `reports/corpus-readiness/`.
- Added checked-in Phase 1 schema artifacts under `schemas/` for extraction records, structural fingerprints, and normalization vocabularies.
- Added `scripts/validate_schema_examples.py` plus `npm run schemas:validate` so the bundled schema examples and enum tables stay aligned with the checked-in contract.
- Chose SQLite as the canonical v1 write store and added `scripts/init_local_store.py` plus `sql/paperview_schema.sql` to initialize the local pipeline database.
- Added `scripts/load_metadata_store.py` plus `npm run store:load-metadata` to populate the SQLite `papers` table from harvested metadata and current local PDF state.
- Verified a full metadata import of `24,203` papers into SQLite and an idempotent rerun over a 5-paper sample.
- Added `scripts/create_pilot_batch.py` plus `npm run pilot:create` to materialize a deterministic abstract-first pilot batch from the SQLite store.
- Generated the first pilot batch with `200` papers, including `53` already-downloaded PDFs and a broad spread of primary categories.
- Added `prompts/abstract-extraction-v1.md` and `scripts/create_extraction_run.py` plus `npm run extract:prepare` to register prompt-ready abstract extraction runs.
- Verified the first prepared extraction run with `200` requests under `data/structural-analogy/runs/abstract_extraction-20260326T003830Z/` and a matching row in SQLite `extraction_runs`.
- Added `scripts/ingest_extraction_responses.py` plus `npm run extract:ingest` to validate and ingest extraction responses into SQLite.
- Verified end-to-end ingestion on a one-record sample response, including an `ingested` run state and a stored `paper_extractions` row.
- Probed the local runtime surface and confirmed `ollama`, `vllm`, `llama.cpp`, and `llm` are not installed here.
- Added `scripts/run_local_mlx_extraction.py` plus `npm run extract:run-mlx` and completed a one-request MLX smoke test with `mlx-community/Qwen2.5-3B-Instruct-4bit`.
- Ingested the MLX smoke-test output successfully; the run path works end to end, but output quality still needs review because schema-valid fields were not yet economically sensible.
- Added `prompts/abstract-extraction-v2.md` with stronger negative-transfer and enum-format rules.
- Prompt v2 improved the smoke-test output by downgrading `tradecore_fit` from `high` to `medium` and removing obviously wrong `decentralized_finance`, but the model still produced semantically wrong domain/portability judgments.
- The latest prompt-v2 smoke-test output is schema-valid after normalization of the outer `paper_id`, but quality is still not good enough for a full 200-paper batch.
- Added `scripts/review_extraction_quality.py` plus `npm run extract:review-quality` to flag semantically suspect outputs from response files.
- Verified the reviewer flags both smoke-test outputs correctly, including overconfident portability/fit labels and unsupported domain assignments.
- Updated the reviewer to classify findings into `blocking` and `warning`, expose a top-level gate status, and exit non-zero with `--fail-on-blocking`.
- Verified both smoke-test outputs remain `blocking` under the new policy and that `--fail-on-blocking` exits with code `2`.
- Added `scripts/review_and_ingest_extractions.py` plus `npm run extract:gate-and-ingest` to enforce review before ingestion.
- Verified the blocking sample refuses ingestion and marks the run as blocked, while a conservative passing sample ingests successfully and updates the stored extraction row.
- Added `prompts/abstract-extraction-v3.md` with explicit positive and negative few-shot examples.
- Verified the v3 smoke-test output for the known-bad CNN portfolio-risk paper now passes the quality gate with `tradecore_fit: low`, `prediction_market_portability: low`, `novel_market_portability: low`, and `original_market_domain: other`.
- Prepared a v3 extraction run slice under `data/structural-analogy/runs/abstract_extraction-v3-pilot10/`.
- Ran the first `10` requests through MLX and reviewed them with the quality gate.
- Result: `8` pass, `1` warning, `1` blocking failure. The main remaining blocker in this slice is semantically overconfident output on a market-microstructure RL paper.
- Updated `scripts/review_extraction_quality.py` to validate each extraction against `schemas/extraction.schema.json` before applying heuristic checks.
- Narrowed the generic-model heuristic so papers with explicit executor-like mechanism terms such as `market making` are not mislabeled as generic-model blockers solely because they use learned policies.
- Updated `scripts/review_and_ingest_extractions.py` to use the schema-aware quality report before gating ingestion.
- Re-ran the first 10-paper v3 slice under the schema-aware gate and corrected the diagnosis: the batch is not blocked by one semantic overreach case, it is blocked by `5` schema-invalid normalization outputs.
- The main Phase 3 blocker is now prompt/schema alignment for enum-limited extraction fields rather than the previously suspected heuristic misclassification.
- Added `prompts/abstract-extraction-v4.md` with explicit invalid-to-valid enum mapping guidance and a market-microstructure example that stays inside the extraction schema.
- Created a fixed-benchmark run under `data/structural-analogy/runs/abstract_extraction-v4-pilot10/` and re-ran the same first 10 papers with the v4 prompt.
- Prompt v4 improved some outputs on the fixed slice: `2206.05410` now maps execution and instrument fields into valid schema categories, and `2501.01278` no longer emits the invalid `finance` domain.
- Prompt v4 did not yet reduce total blocking count under the schema-aware gate: the fixed slice remains `5/10` blocking, with a new heuristic blocker on `2004.13000` and continued enum drift on several non-market papers.
- The next Phase 3 issue is now narrower: tighten or suppress the generic-model heuristic on clearly non-finance optimization papers, or further constrain the prompt so those papers collapse fully to conservative `other` outputs.
- Added `prompts/abstract-extraction-v5.md` with an explicit off-domain collapse rule for non-market optimization papers and a negative example based on the `math.OC` / drone-logistics failure mode.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v5-offdomain-smoke/` for `2004.13000`.
- Prompt v5 resolves that specific blocker class in smoke-test form: `2004.13000` now produces a schema-valid all-`other`, `tradecore_fit: low`, low-portability extraction and passes the quality gate.
- The next unresolved question is whether the same v5 improvement reduces the blocking count when rerun across the fixed 10-paper benchmark slice.
- Built a fixed-benchmark run under `data/structural-analogy/runs/abstract_extraction-v5-pilot10/` and re-ran the same first 10 papers with prompt v5.
- Prompt v5 materially improves batch quality on the fixed slice: `v3 = 5/10 blocking`, `v4 = 5/10 blocking`, `v5 = 1/10 blocking` under the schema-aware gate.
- The remaining blocker on the fixed slice is `2002.02583`, where the model still emits the unsupported edge label `triangular_arbitrage` instead of collapsing to `cross_venue_basis` or `other`.
- Prompt v5 is now the active prompt iteration for Phase 3 because it is the first version to produce a real blocker-count reduction on the fixed benchmark.
- Added `prompts/abstract-extraction-v6.md` with an explicit FX triangular-arbitrage mapping example that keeps `edge_source` inside the schema.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v6-fxarb-smoke/` for `2002.02583`.
- Prompt v6 resolves that final blocker class in smoke-test form: `2002.02583` now maps `edge_source` to `cross_venue_basis`, remains schema-valid, and passes the quality gate.
- The next unresolved question is whether the same v6 improvement brings the fixed 10-paper benchmark from `1/10` blocking down to `0/10`.
- Built a fixed-benchmark run under `data/structural-analogy/runs/abstract_extraction-v6-pilot10/` and re-ran the same first 10 papers with prompt v6.
- Prompt v6 clears the fixed benchmark under the schema-aware gate: `v5 = 1/10 blocking`, `v6 = 0/10 blocking`.
- Prompt v6 is now the active extraction prompt for Phase 3 because it is the first version to pass the full fixed benchmark slice cleanly.
- The next Phase 3 issue is to widen beyond the fixed 10-paper benchmark, likely by reviewing the first 25-paper or 50-paper slice under the same gate before attempting the full 200-paper pilot.
- Built a wider review run under `data/structural-analogy/runs/abstract_extraction-v6-pilot25/` and ran the first `25` requests with prompt v6.
- The first wider slice does not stay fully clean: `25` reviewed, `2` blocking, `0` warning, `8%` flagged ratio.
- The two blocker papers on the `25`-paper slice are:
  - `2205.01524` (`q-fin.RM` joint default / credit-risk ML paper), which drifts into invalid `original_market_domain = credit_risk` and overstates `tradecore_fit`.
  - `2008.00925` (`q-fin.CP` numerical American-option solver), which overstates `tradecore_fit` as `medium` despite being a pricing algorithm paper rather than an executable market mechanism.
- The next Phase 3 issue is now explicit: add targeted suppression/examples for these two wider-slice blocker classes before widening further or ingesting beyond the benchmark set.
- Added `prompts/abstract-extraction-v7.md` with an explicit numerical-pricing / PDE-solver suppression rule and a dedicated American-option pricer example.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v7-pricer-smoke/` for `2008.00925`.
- Prompt v7 resolves the numerical-pricer blocker in targeted smoke-test form: `2008.00925` now remains schema-valid with `tradecore_fit = low` and passes the quality gate.
- The next unresolved blocker from the wider `25`-paper slice is `2205.01524`, the generic credit-risk ML paper.
- Added `prompts/abstract-extraction-v8.md` with an explicit credit-risk / joint-default suppression rule and a dedicated credit-risk ML example.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v8-credit-smoke/` for `2205.01524`.
- Prompt v8 resolves the generic credit-risk blocker in targeted smoke-test form: `2205.01524` now maps to `original_market_domain = other`, `tradecore_fit = low`, remains schema-valid, and passes the quality gate.
- Added `--max-requests` to `scripts/create_extraction_run.py` so widened benchmark slices can be regenerated directly from the active prompt file instead of by copying stale `requests.jsonl` artifacts.
- Discovered that a copied-request `v8` wider-slice rerun was invalid because the embedded request prompts still contained the old prompt body even though the run metadata had changed.
- Rebuilt `data/structural-analogy/runs/abstract_extraction-v8-pilot25/` from `prompts/abstract-extraction-v8.md` using `create_extraction_run.py --max-requests 25` and re-ran the slice through the MLX backend.
- The first valid `v8` wider-slice rerun improves the `25`-paper slice from `2/25` blocking to `1/25` blocking under the schema-aware gate.
- The remaining widened-slice blocker is `2412.03618`, where the model still emits `original_market_domain = equities|options|futures|fixed_income|fx|other` and overstates `tradecore_fit` / `prediction_market_portability` on a generic portfolio-risk paper.
- Added `prompts/abstract-extraction-v9.md` with an explicit multi-asset portfolio-risk collapse rule for mixed-domain generic risk papers.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v9-portfolio-smoke/` for `2412.03618`.
- Prompt v9 resolves the remaining widened-slice blocker in targeted smoke-test form: `2412.03618` now maps to `original_market_domain = other`, `tradecore_fit = low`, and low portability while remaining schema-valid and gate-clean.
- Built a full widened rerun under `data/structural-analogy/runs/abstract_extraction-v9-pilot25/` and re-ran the `25`-paper slice with prompt v9.
- The full v9 rerun regresses badly: `20/25` blocking under the schema-aware gate, with `18` rows missing required `mechanism_name` and other batch-stability failures.
- Prompt v9 should remain a targeted blocker-fix experiment, not the active widened-slice batch prompt.
- The next Phase 3 issue is now to merge the `2412.03618` fix back into the stronger v8 prompt surface without losing required fields or reintroducing old blockers.
- Added `prompts/abstract-extraction-v10.md` as a merged prompt candidate built from the stronger v8 surface plus the narrow multi-asset portfolio-risk fix from v9.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v10-portfolio-smoke/` for `2412.03618`.
- Prompt v10 resolves `2412.03618` cleanly in smoke-test form while preserving required fields such as `mechanism_name`, making it the next widened-rerun candidate.
- Built a full widened rerun under `data/structural-analogy/runs/abstract_extraction-v10-pilot25/` and re-ran the `25`-paper slice with prompt v10.
- Prompt v10 clears the widened slice: `v8 = 1/25` blocking, `v10 = 0/25` blocking under the schema-aware gate.
- The widened abstract-extraction surface is now clean enough to consider the first gate-and-ingest pass beyond the benchmark set.
- Ran `scripts/review_and_ingest_extractions.py` on `abstract_extraction-v10-pilot25`.
- The first beyond-benchmark gate-and-ingest pass succeeded: `25` rows inserted, `0` invalid, and the run state is now `ingested`.
- `paper_extractions` now contains `26` rows total, with `25` from the widened v10 slice and the earlier single-row sample.
- Built a larger review run under `data/structural-analogy/runs/abstract_extraction-v10-pilot50/` and ran the first `50` requests with prompt v10.
- The first larger v10 slice does not stay clean: `50` reviewed, `3` blocking, `1` warning, `8%` flagged ratio.
- New blocker IDs on the `50`-paper slice are:
  - `2510.07444` with invalid `original_market_domain = debt`
  - `2210.15329` with invalid pipe-joined `original_market_domain = equities|corporate_bonds|government_bonds`
  - `2511.17963` with invalid `edge_source = trend_following` plus over-high fit
- The first larger warning-only case is `2103.11557`, which drifts into unsupported `decentralized_finance` labeling.
- The next Phase 3 issue is now to retire these newly exposed blocker classes in targeted smoke-test form before considering any larger-batch ingestion.
- Added `prompts/abstract-extraction-v11.md` as a first debt/loan blocker fix attempt, but it did not move `2510.07444`; the model still emitted `original_market_domain = debt`.
- Added `prompts/abstract-extraction-v12.md` with a stronger debt/loan portfolio-risk collapse rule plus a concrete lending/VaR negative example.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v12-debt-smoke/` for `2510.07444`.
- Prompt v12 resolves the `2510.07444` blocker in targeted smoke-test form: the output now uses `original_market_domain = other`, `instrument_type = ["other"]`, and low fit/portability while remaining gate-clean.
- Added `prompts/abstract-extraction-v13.md` with a targeted collapse rule for climate-transition investment-fund exposure papers plus an explicit full-key requirement for conservative outputs.
- Built targeted smoke runs under `data/structural-analogy/runs/abstract_extraction-v13-climate-smoke/`, `data/structural-analogy/runs/abstract_extraction-v13-climate-smoke-r2/`, and `data/structural-analogy/runs/abstract_extraction-v13-climate-smoke-r3/` for `2210.15329`.
- The first two `2210.15329` v13 smoke runs fixed the enum drift but dropped `mechanism_name`, which confirmed that targeted blocker fixes still need a full-schema output contract.
- Prompt v13 resolves the `2210.15329` blocker in targeted smoke-test form on the third run: the output now uses `original_market_domain = other`, preserves `mechanism_name` and `mechanism_summary`, and passes the schema-aware gate cleanly.
- Added `prompts/abstract-extraction-v14.md` with a targeted collapse rule for hybrid forecasting-plus-reinforcement-learning portfolio optimization papers.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v14-portfolio-rl-smoke/` for `2511.17963`.
- Prompt v14 resolves the `2511.17963` blocker in targeted smoke-test form: the output now uses `original_market_domain = other`, `edge_source = ["other"]`, `tradecore_fit = low`, and passes the schema-aware gate cleanly.
- Built a full verification rerun under `data/structural-analogy/runs/abstract_extraction-v14-pilot50/` and re-ran the first `50` papers with the merged v14 prompt line.
- The first full v14 `50`-paper rerun is still blocking: `4/50` blocking, `0` warning.
- Remaining blocker IDs on the v14 `50`-paper rerun are:
  - `2205.01524` with missing required `mechanism_name`
  - `cond-mat/0012514` with missing required `mechanism_name`
  - `cond-mat/0108452` with missing required `mechanism_name`
  - `2510.07444` regressed back to invalid `debt` / `loan` labeling despite the earlier v12 targeted smoke-test success
- Built a targeted regression smoke run under `data/structural-analogy/runs/abstract_extraction-v14-debt-regression-smoke/` and confirmed that `2510.07444` still fails in isolation under the merged v14 prompt line, so the regression is in the prompt itself rather than batch context.
- Added `prompts/abstract-extraction-v15.md` with an explicit all-`other` collapse for generic debt/loan VaR papers across `edge_source`, `execution_style`, `required_market_conditions`, and `main_failure_modes`.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v15-debt-smoke/` for `2510.07444`.
- Prompt v15 resolves the `2510.07444` regression in targeted smoke-test form: the output now uses `original_market_domain = other`, `instrument_type = ["other"]`, `edge_source = ["other"]`, `execution_style = ["other"]`, and passes the schema-aware gate cleanly.
- Added `prompts/abstract-extraction-v16.md` with a stronger contract for conservative-collapse outputs: even all-`other` rows must derive `mechanism_name` and `mechanism_summary` from the title/topic.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v16-missing-name-smoke-2205/` for `2205.01524`.
- Prompt v16 resolves the representative missing-name blocker in targeted smoke-test form: `2205.01524` now stays low-fit all-`other` while preserving `mechanism_name` and `mechanism_summary`, and it passes the schema-aware gate cleanly.
- Built a targeted multi-paper smoke run under `data/structural-analogy/runs/abstract_extraction-v16-missing-name-condmat-smoke/` for `cond-mat/0012514` and `cond-mat/0108452`.
- Prompt v16 resolves the remaining missing-required-key blockers in targeted smoke-test form: both cond-mat papers now preserve `mechanism_name` and `mechanism_summary`, and both pass the schema-aware gate.
- One semantic quality issue remains in that smoke run: `cond-mat/0108452` uses placeholder `mechanism_name = "None"` even though the row is schema-valid.
- Updated `scripts/review_extraction_quality.py` so placeholder mechanism names like `None`, `N/A`, `unknown`, `null`, or empty string are now blocking failures.
- Re-reviewed `data/structural-analogy/runs/abstract_extraction-v16-missing-name-condmat-smoke/responses.targets.jsonl` and confirmed the tightened reviewer now blocks `cond-mat/0108452` correctly for `placeholder_mechanism_name`.
- Added `prompts/abstract-extraction-v17.md` with an explicit prompt rule forbidding placeholder `mechanism_name` and `mechanism_summary` values.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v17-placeholder-smoke/` for `cond-mat/0108452`.
- Prompt v17 does not yet fix the generation side: the model still emits `mechanism_name = "None"` on `cond-mat/0108452`, and the tightened reviewer correctly blocks it.
- Added `prompts/abstract-extraction-v18.md` with an explicit negative example for statistical-scaling / fractal market time-series papers that requires a title-derived non-placeholder mechanism name.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v18-scaling-name-smoke/` for `cond-mat/0108452`.
- Prompt v18 resolves the placeholder-name generation failure in targeted smoke-test form: `cond-mat/0108452` now produces `mechanism_name = "Scaling analysis of stock index time series"` and passes the tightened reviewer cleanly.
- Built a full verification rerun under `data/structural-analogy/runs/abstract_extraction-v18-pilot50/` and re-ran the first `50` papers with the merged v18 prompt line.
- The full v18 `50`-paper rerun materially improves the larger-batch result: `2/50` blocking, `1/50` warning, versus `4/50` blocking and `0` warning on the earlier v14 verification run.
- Remaining flagged papers on the v18 `50`-paper rerun are:
  - `2206.05410` with invalid `required_market_conditions[1] = inventory_pressure`
  - `2103.11557` with invalid `original_market_domain = venture_capital`
  - `2311.02434` as a warning-only `domain_not_supported:decentralized_finance`
- Added `prompts/abstract-extraction-v19.md` with an explicit market-making schema-alignment rule: keep `inventory_pressure` and `queue_position_value` only in `edge_source`, and use market-structure values like `thin_book` or `observable_order_book` in `required_market_conditions`.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v19-mm-smoke/` for `2206.05410`.
- Prompt v19 resolves the `2206.05410` blocker in targeted smoke-test form: the output now keeps `inventory_pressure` in `edge_source`, collapses `required_market_conditions` to `["thin_book"]`, preserves the rest of the market-making extraction structure, and passes the schema-aware gate cleanly.
- Added `prompts/abstract-extraction-v20.md` with a first venture-capital collapse rule, but the targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v20-vc-smoke/` showed that rule-only prompting was not enough: `2103.11557` still emitted unsupported `original_market_domain = venture_capital`.
- Added `prompts/abstract-extraction-v21.md` with an explicit venture-capital exit-timing example that shows the full low-fit collapse pattern.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v21-vc-smoke/` for `2103.11557`.
- Prompt v21 resolves the `2103.11557` blocker in targeted smoke-test form: the output now uses `original_market_domain = other`, keeps the rest of the row conservative, preserves required descriptive fields, and passes the schema-aware gate cleanly.
- Updated `scripts/review_extraction_quality.py` so explicit DeFi / DAO / blockchain cues count as support for `original_market_domain = decentralized_finance`.
- Re-reviewed the original `data/structural-analogy/runs/abstract_extraction-v18-pilot50/responses.first50.jsonl` batch into `data/structural-analogy/runs/abstract_extraction-v18-pilot50/responses.first50.quality.v2.json`.
- The refreshed `v18` report removes the old `2311.02434` warning entirely: the larger-batch baseline is now `2/50` blocking and `0/50` warning.
- Added `prompts/abstract-extraction-v22.md` as the first merged larger-batch candidate built from the stable `v18` surface plus the prompt-side fixes from `v19` and `v21`.
- Built and ran a full `50`-paper rerun under `data/structural-analogy/runs/abstract_extraction-v22-pilot50/`.
- The full `v22` `50`-paper rerun materially improves the larger-batch result again: `1/50` blocking and `0/50` warning.
- The only remaining blocker in the `v22` rerun is `2002.02583`, where the extraction claims `tradecore_fit = high` and `novel_market_portability = high` but still leaves `why_missed = ["other"]`, triggering `high_fit_without_specific_why_missed`.
- Added `prompts/abstract-extraction-v23.md` with an explicit rule that `tradecore_fit = high` outputs may not leave `why_missed = ["other"]`, plus a concrete FX triangular-arbitrage example using `buried_in_non_prediction_market_language` and `requires_linked_market_modeling`.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v23-fx-smoke/` for `2002.02583`.
- Prompt v23 resolves the `2002.02583` blocker in targeted smoke-test form: the output now keeps the high-fit linked-market framing, uses specific `why_missed` reasons, and passes the schema-aware gate cleanly.
- Built and ran a full `50`-paper rerun under `data/structural-analogy/runs/abstract_extraction-v23-pilot50/`.
- The full `v23` `50`-paper rerun regresses badly to `9/50` blocking. The main new failure modes are broad high-fit / high-portability overreach on generic papers and an invalid `Q_learning` execution label reappearing on `2206.05410`.
- Prompt v23 should remain a targeted comparison branch, not the new active larger-batch prompt.
- Added `prompts/abstract-extraction-v24.md` as a narrower merge candidate built from the stronger `v22` batch surface plus only the targeted FX exemplar from `v23`, without the broad global high-fit `why_missed` rule.
- Built a targeted smoke run under `data/structural-analogy/runs/abstract_extraction-v24-fx-smoke/` for `2002.02583`.
- Prompt v24 resolves `2002.02583` cleanly in targeted smoke-test form: the output keeps the high-fit FX linked-market framing, uses specific `why_missed` reasons, and passes the schema-aware gate without the broader v23 rule changes.
- Built and ran a full `50`-paper rerun under `data/structural-analogy/runs/abstract_extraction-v24-pilot50/`.
- The full `v24` `50`-paper rerun materially improves on `v23`, but it still lands at `4/50` blocking and `0/50` warning.
- The remaining failures are now narrower `high_fit_without_specific_why_missed` cases, especially `2206.05410` and `1310.6873`, rather than the broad overreach and enum-regression pattern seen in `v23`.
- The next Phase 3 issue is now to retire these narrower high-fit / specific-why-missed failures before another larger-batch verification or the first `50`-paper gate-and-ingest attempt.
- Added `prompts/abstract-extraction-v25.md` as a targeted off-domain fix branch for political-science measurement and AI ethics / moral-agent papers.
- Built a targeted multi-paper smoke run under `data/structural-analogy/runs/abstract_extraction-v25-offdomain-smoke/` for `2301.11084` and `2305.11519`.
- Prompt v25 resolves those two generic off-domain overreach papers in targeted smoke-test form: both now stay `tradecore_fit = low`, both portability fields stay `low`, and the schema-aware gate passes cleanly.
- The remaining larger-batch work is now narrower: the unresolved `v24` blockers are the genuinely market-adjacent high-fit papers (`2206.05410` and `1310.6873`) that still need specific `why_missed` reasons before another full `50`-paper rerun.

## Summary

This repo now has the full arXiv `q-fin` metadata set and an in-progress PDF pull. The next step is not generic paper clustering. It is to build a local-first literature review system that extracts market mechanisms from papers, normalizes them into a controlled ontology, and searches for structurally similar ideas in adjacent literatures that could transfer into Kalshi/Polymarket-style markets before they are fully exploited.

The output of the system is not a prettier embedding map. It is a ranked list of candidate strategy mechanisms with explicit transfer arguments, implementation fit against current `tradecore` strategy muscles, and a review queue for the highest-value “diamond in the rough” ideas.

---

## Goal

Build a local-first `structural analogy engine` that answers:

1. Which literature mechanisms are structurally similar to the strategies `tradecore` is already capable of expressing?
2. Which of those mechanisms come from non-obvious domains rather than standard prediction-market or q-fin papers?
3. Which mechanisms have a credible path into novel event markets and are still plausibly underexploited?

## Why This Exists

A standard embedding workflow will mostly recover obvious neighbors:

- more cross-venue parity papers
- more prediction-market efficiency papers
- more well-known microstructure and arbitrage papers

That is not the objective. The objective is to find strategy primitives that:

- live in adjacent but non-obvious literatures
- share the same constraint geometry as the target markets
- can be turned into executable setups by the current or near-future `tradecore` stack

## Guiding Principle

Treat each paper as a source of:

- a human-readable mechanism description
- a machine-readable structural fingerprint

The fingerprint is the retrieval object. It captures payoff topology, frictions, participant incentives, time structure, and execution shape, so the system can find analogies across fields even when vocabulary is unrelated.

---

## What The System Produces

Primary outputs:

- `mechanism library`: normalized records of extracted strategy mechanisms
- `structural index`: embeddings + graph edges over summaries and fingerprints
- `transfer map`: source domain -> target market portability records
- `candidate backlog`: ranked strategy ideas that can be reviewed and turned into `tradecore` executors or setup families

Secondary outputs:

- retrieval notebook / dashboard
- paper review queue
- evidence packets for top candidates

---

## Scope

### In scope

- local ingestion of metadata and PDFs
- text extraction from PDFs
- section-aware chunking
- LLM extraction into a JSON schema
- normalization into controlled vocabularies
- embeddings for summaries and fingerprints
- graph construction and retrieval
- scoring for novelty, portability, and `tradecore` fit
- manual review loop for final candidate selection

### Out of scope for v1

- automatic backtesting
- live trading integration
- a polished UI
- exhaustive full-text deep reasoning on all papers before triage
- perfect paper parsing from every PDF edge case

---

## Corpus Strategy

Do not rely on `q-fin` alone. The review engine should treat `q-fin` as the anchor corpus and expand into adjacent domains where structural analogs are more likely to hide.

Priority corpora:

- arXiv `q-fin`
- arXiv `econ`
- arXiv `stat`
- arXiv `cs` where relevant to market design, auctions, RL, and mechanism design
- prediction market literature
- sportsbook / betting market efficiency literature
- market microstructure
- auction theory
- DeFi AMM / liquidity incentive papers
- electricity / weather / catastrophe / other fragmented market papers

V1 can start with `q-fin` plus a deliberately selected adjacent slice rather than attempting every domain at once.

---

## System Design

## 1. Ingest

Inputs:

- `data/arxiv-qfin/metadata.jsonl`
- downloaded PDFs under `data/arxiv-qfin/pdfs/`

Initial storage:

- `papers`
- `paper_sections`
- `paper_extractions` as a transitional staging table
- `mechanism_instances` as the canonical analysis unit
- `mechanism_evidence_spans`
- `transfer_hypotheses`
- `candidate_families`
- `analyst_labels`
- `benchmark_pairs`
- `mechanism_fingerprints`
- `paper_embeddings`
- `paper_edges`
- `strategy_candidates`

Recommended local store:

- `duckdb` or `sqlite` for metadata and extraction outputs
- parquet files for intermediate batches if needed

## 2. Text Extraction

Pipeline:

1. extract raw text from PDF
2. detect high-value sections
3. preserve section labels
4. store cleaned text by section

Preferred sections:

- abstract
- introduction
- model / setup
- empirical strategy
- conclusion

Rationale:

Mechanisms are easier to recover from section-aware extraction than from arbitrary token chunks.

## 3. Structured Extraction

Each paper may yield `0..N` mechanism records.

Human-readable fields:

- `mechanism_name`
- `mechanism_summary`
- `original_market_domain`
- `instrument_type`
- `edge_source`
- `execution_style`
- `holding_horizon`
- `evidence_strength`
- `main_failure_modes`
- `notes`

Transfer fields:

- `prediction_market_portability`
- `novel_market_portability`
- `tradecore_fit`
- `likely_crowding`
- `why_missed`

The extraction pass should prefer compact JSON over prose.

## 4. Structural Fingerprint

Each accepted mechanism instance also gets a normalized fingerprint.

Core dimensions:

- `topology`
- `market_structure`
- `mispricing_source`
- `execution_pattern`
- `participant_pressure`
- `time_structure`
- `risk_controls`
- `transfer_targets`
- `tradecore_fit`

Examples of normalized values:

- `topology`: `two_leg_parity`, `n_leg_basket`, `term_structure`, `implication_graph`, `queue_value_mm`
- `mispricing_source`: `logical_inconsistency`, `fragmentation`, `stale_quotes`, `inventory_pressure`, `reward_incentives`, `settlement_friction`
- `execution_pattern`: `maker_anchor`, `parallel_fok`, `sequential_fok`, `quote_ladder`, `recovery_gtc`

This is the key artifact. It is what allows “electricity market congestion paper” and “prediction market event path arb” to look adjacent even if they use different terminology.

## 5. Normalization

Do not search over raw free text. Normalize extracted values into a small controlled ontology.

Use a two-pass process:

1. extraction pass emits raw JSON
2. normalization pass maps raw strings into enums and canonical labels

This will make retrieval far more reliable than one-step prompting.

## 6. Embeddings

Generate separate embeddings for:

- title + abstract
- mechanism summary
- serialized structural fingerprint

The fingerprint embedding is the important non-obvious search surface. The abstract embedding is mostly a baseline.

## 7. Graph Construction

Connect papers through:

- fingerprint overlap
- summary embedding similarity
- shared execution shape
- shared friction patterns across different domains

This allows retrieval of:

- close structural matches
- far analogs with low vocabulary overlap
- bridge papers that connect otherwise separate literatures

## 8. Opportunity Scoring

Each extracted mechanism should receive a score made of:

- `tradecore_fit_score`
- `structural_similarity_score`
- `novelty_score`
- `evidence_score`
- `crowding_penalty`
- `implementation_burden_penalty`

Target outcome:

A paper that looks strange on the surface but fits existing executor muscles should rank above another obvious prediction-market paper saying something everyone already knows.

## 9. Human Review Queue

The system should not auto-decide the best strategies. It should create review packets containing:

- top candidate mechanism
- why it matched
- source domain
- transfer argument
- fit with current `tradecore` capabilities
- key assumptions
- reasons it may still be underexploited

This queue is where actual strategy design begins.

---

## Retrieval Modes

The engine should support three retrieval modes.

### 1. Nearest fit

Find papers that look most similar to current strategy families.

Use when:

- expanding an existing setup family
- finding better guards, execution patterns, or edge refinements

### 2. Far analog

Find papers with high structural overlap and low vocabulary overlap.

Use when:

- looking for the diamond in the rough
- trying to escape obvious q-fin neighbors

This should be treated as the highest-value search mode.

### 3. Bridge papers

Find papers that connect two clusters that rarely touch.

Use when:

- searching for mechanism transfer between domains
- identifying papers that may “translate” one field into another

---

## Fit Against Current `tradecore` Muscle

The engine should explicitly score whether a mechanism can be expressed by the current or near-future strategy stack.

Current visible muscles:

- maker-anchor then taker-hedge
- FOK-first short-window execution
- n-leg basket completion
- GTC recovery after partial fill
- stale-data / venue-health / reconciliation discipline
- reward-aware maker behavior

A candidate mechanism should be easier to prioritize if it maps cleanly onto one of:

- parity / basis setups
- completeness / sum-to-par setups
- implication graph setups
- term-structure inconsistencies
- queue-value or inventory-aware MM

This prevents the review from drifting into abstract finance theory that cannot become a strategy.

---

## Build Plan

## Phase 0. Corpus readiness

Status: `in_progress`
Owner: `unassigned`
Exit criteria status: `partial`
Comments:

- Metadata is complete.
- `scripts/corpus_status.py` now provides the canonical corpus-readiness check.
- `scripts/launch_qfin_download.py` now provides the canonical detached launch path.
- `scripts/corpus_inventory.py` now provides the canonical completeness inventory.
- `npm run corpus:status` now refreshes stale inventory automatically, so operators do not need to remember a separate refresh step.
- The downloader now records permanent no-PDF cases explicitly in `failures.jsonl`.
- The downloader now records exhausted server-side failures as retryable `5xx` failures instead of generic unknown failures.
- Inventory now records canonical failure artifacts instead of relying on the raw `failures.jsonl` stream directly.
- Retryable failures can now be materialized and re-run from canonical inventory artifacts.
- An automated pipeline path now exists for the main pull followed by a bounded retry pass.
- A single readiness report artifact now exists for Phase 0 review and closeout.
- PDF pull is not complete, but the downloader has been relaunched and is currently running.
- Download-gap inventory exists; parse-failure inventory does not yet exist because PDF text extraction has not started.
- Relevant artifacts:
  - `scripts/corpus_status.py`
  - `scripts/launch_qfin_download.py`
  - `scripts/corpus_inventory.py`
  - `logs/qfin_download.log`
  - `logs/qfin_download.pid`
  - `logs/qfin_download.launch.json`
  - `data/arxiv-qfin/inventory/summary.json`

Deliverables:

- confirm full PDF pull
- create local data directory layout
- choose local DB
- define file naming and batch IDs

Success criteria:

- every harvested paper has metadata and either extracted text or an explicit parse failure record

## Phase 1. Schema and ontology

Status: `in_progress`
Owner: `unassigned`
Exit criteria status: `partial`
Comments:

- Draft schema and fingerprint are no longer prose-only; the checked-in source of truth now lives under `schemas/`.
- A minimal validator now checks example records and enum tables against the checked-in schema files.
- SQLite is now the canonical local write store for the pilot, and the repo can initialize it with `npm run store:init`.
- The repo can now populate the canonical `papers` table with `npm run store:load-metadata`.
- The repo can now materialize a deterministic abstract-first pilot batch with `npm run pilot:create`.
- Enum coverage still needs to be hardened against real extraction outputs and adjacent-domain edge cases.
- Relevant artifacts:
  - `schemas/extraction.schema.json`
  - `schemas/fingerprint.schema.json`
  - `schemas/normalization_vocab.json`
  - `schemas/examples/extraction.example.json`
  - `schemas/examples/fingerprint.example.json`
  - `scripts/validate_schema_examples.py`
  - `sql/paperview_schema.sql`
  - `scripts/init_local_store.py`
  - `scripts/load_metadata_store.py`
  - `scripts/create_pilot_batch.py`
  - `data/structural-analogy/pilots/abstract-pilot-v1/summary.json`

Deliverables:

- extraction JSON schema
- normalization vocabularies
- initial `tradecore` fit categories

Success criteria:

- schema covers at least 90% of papers in a 50-paper pilot without major redesign

## Phase 2. Text extraction and sectioning

Status: `planned`
Owner: `unassigned`
Exit criteria status: `not_started`
Comments:

- Parser choice not yet locked.

Deliverables:

- local PDF extraction pipeline
- section-aware storage
- parse-quality metrics

Success criteria:

- pilot papers produce usable abstract / intro / conclusion text with manageable cleanup effort

## Phase 3. Local extraction pipeline

Status: `in_progress`
Owner: `unassigned`
Exit criteria status: `partial`
Comments:

- Abstract-first pilot inputs now exist as deterministic pilot-batch artifacts.
- Prompt-ready extraction run artifacts can now be created and registered in SQLite before picking the concrete local model stack.
- Response ingestion and schema validation now exist for prepared runs.
- The first local execution backend is now MLX on Apple Silicon with `mlx-community/Qwen2.5-3B-Instruct-4bit`.
- A one-request smoke test completed end to end, but the resulting schema-valid extraction still showed weak semantic quality, so batch execution should wait for prompt/model iteration.
- Prompt v3 is the current active iteration for abstract extraction quality work.
- Prompt v6 is now the active prompt/schema-alignment iteration for abstract extraction.
- Prompt v6 remains the active prompt, but the first wider `25`-paper review slice has now exposed two new blocker classes beyond the fixed benchmark set.
- Prompt v7 now exists as the targeted numerical-pricer suppression experiment for the `2008.00925` blocker class.
- Prompt v8 now exists as the targeted credit-risk suppression experiment for the `2205.01524` blocker class.
- Prompt v9 now exists as the targeted multi-asset portfolio-risk suppression experiment for the `2412.03618` blocker class.
- Prompt v10 now exists as the merged widened-rerun candidate: v8 batch surface plus the narrow `2412.03618` fix from v9.
- Prompt v8 has now been re-run on the wider `25`-paper slice using regenerated request artifacts rather than copied request files.
- The first valid v8 wider-slice rerun improves the slice from `2/25` blocking to `1/25` blocking, but does not yet clear the gate.
- Prompt v9 now retires the remaining wider-slice blocker in targeted smoke-test form for `2412.03618`.
- The full v9 widened rerun is not usable as the next active prompt: it regresses to `20/25` blocking because many rows lose required fields like `mechanism_name`.
- Prompt v10 now passes the same `2412.03618` targeted smoke test while preserving the v8-style required field surface.
- Prompt v10 now also clears the full widened `25`-paper slice at `0/25` blocking and becomes the new active widened-slice prompt.
- The first beyond-benchmark gate-and-ingest pass has now completed on the widened v10 slice.
- The first larger v10 review slice has now been run and is currently a diagnosis set, not an ingest candidate.
- Prompt v12 now exists as the targeted debt/loan larger-slice blocker fix for `2510.07444`.
- Prompt v19 now exists as the targeted market-making schema-alignment fix for `2206.05410`.
- Prompt v21 now exists as the targeted venture-capital exit-timing domain-collapse fix for `2103.11557`.
- Prompt v25 now exists as the targeted off-domain collapse fix for political-science measurement and AI ethics / moral-agent papers.
- Prompt v25 retires the two generic off-domain overreach papers from the `v24` blocker set in targeted smoke-test form.
- Relevant artifacts:
  - `prompts/abstract-extraction-v9.md`
  - `data/structural-analogy/runs/abstract_extraction-v9-portfolio-smoke/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v9-portfolio-smoke/responses.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v9-portfolio-smoke/responses.quality.json`
  - `data/structural-analogy/runs/abstract_extraction-v9-pilot25/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v9-pilot25/responses.first25.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v9-pilot25/responses.first25.quality.json`
  - `prompts/abstract-extraction-v10.md`
  - `data/structural-analogy/runs/abstract_extraction-v10-portfolio-smoke/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v10-portfolio-smoke/responses.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v10-portfolio-smoke/responses.quality.json`
  - `data/structural-analogy/runs/abstract_extraction-v10-pilot25/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v10-pilot25/responses.first25.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v10-pilot25/responses.first25.quality.json`
  - `data/structural-analogy/runs/abstract_extraction-v10-pilot25/gate_summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v10-pilot25/ingest_summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v10-pilot50/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v10-pilot50/responses.first50.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v10-pilot50/responses.first50.quality.json`
  - `prompts/abstract-extraction-v12.md`
  - `data/structural-analogy/runs/abstract_extraction-v12-debt-smoke/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v12-debt-smoke/request.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v12-debt-smoke/responses.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v12-debt-smoke/responses.target.quality.json`
  - `prompts/abstract-extraction-v19.md`
  - `data/structural-analogy/runs/abstract_extraction-v19-mm-smoke/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v19-mm-smoke/request.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v19-mm-smoke/responses.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v19-mm-smoke/responses.target.quality.json`
  - `prompts/abstract-extraction-v20.md`
  - `data/structural-analogy/runs/abstract_extraction-v20-vc-smoke/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v20-vc-smoke/request.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v20-vc-smoke/responses.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v20-vc-smoke/responses.target.quality.json`
  - `prompts/abstract-extraction-v21.md`
  - `data/structural-analogy/runs/abstract_extraction-v21-vc-smoke/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v21-vc-smoke/request.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v21-vc-smoke/responses.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v21-vc-smoke/responses.target.quality.json`
  - `prompts/abstract-extraction-v22.md`
  - `data/structural-analogy/runs/abstract_extraction-v22-pilot50/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v22-pilot50/responses.first50.rerun.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v22-pilot50/responses.first50.quality.json`
  - `prompts/abstract-extraction-v23.md`
  - `data/structural-analogy/runs/abstract_extraction-v23-fx-smoke/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v23-fx-smoke/request.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v23-fx-smoke/responses.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v23-fx-smoke/responses.target.quality.json`
  - `data/structural-analogy/runs/abstract_extraction-v23-pilot50/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v23-pilot50/responses.first50.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v23-pilot50/responses.first50.quality.json`
  - `prompts/abstract-extraction-v24.md`
  - `data/structural-analogy/runs/abstract_extraction-v24-fx-smoke/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v24-fx-smoke/request.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v24-fx-smoke/responses.target.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v24-fx-smoke/responses.target.quality.json`
  - `data/structural-analogy/runs/abstract_extraction-v24-pilot50/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v24-pilot50/responses.first50.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v24-pilot50/responses.first50.quality.json`
  - `prompts/abstract-extraction-v25.md`
  - `data/structural-analogy/runs/abstract_extraction-v25-offdomain-smoke/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v25-offdomain-smoke/requests.targets.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v25-offdomain-smoke/responses.targets.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v25-offdomain-smoke/responses.targets.quality.json`
  - `data/structural-analogy/runs/abstract_extraction-v18-pilot50/responses.first50.quality.v2.json`
- A heuristic quality-review gate now exists for smoke-test and pilot-batch outputs.
- The quality-review gate now has an operational blocking policy, not just diagnostics.
- The quality-review gate is now schema-aware and blocks unsupported enum labels before ingestion.
- The repo now has a single gate-and-ingest command for policy-compliant extraction persistence.
- A first wider slice has now been run against the active prompt and reviewed before ingestion.
- The original diagnosis of the first wider slice was incomplete because the reviewer only checked heuristics; schema-aware review now shows normalization drift is the primary blocker.
- A v4 prompt iteration has now been benchmarked against the same 10-paper slice, confirming partial improvement but no net reduction in blocking count yet.
- A v5 prompt iteration has now been smoke-tested against the off-domain `math.OC` blocker and passes on that targeted case.
- A v5 prompt iteration has now been benchmarked against the full fixed 10-paper slice and reduces the schema-aware blocking count to `1/10`.
- A v6 prompt iteration has now been smoke-tested against the final fixed-slice blocker and passes on that targeted case.
- A v6 prompt iteration has now been benchmarked against the full fixed 10-paper slice and clears the schema-aware gate at `0/10` blocking.
- A v6 prompt iteration has now been run on the first wider `25`-paper slice and yields `2/25` blocking under the same gate.
- A v7 prompt iteration has now been smoke-tested against the numerical American-option pricer blocker and passes on that targeted case.
- A v8 prompt iteration has now been smoke-tested against the generic credit-risk ML blocker and passes on that targeted case.
- Relevant artifacts:
  - `prompts/abstract-extraction-v1.md`
  - `prompts/abstract-extraction-v2.md`
  - `prompts/abstract-extraction-v3.md`
  - `scripts/create_extraction_run.py`
  - `scripts/run_local_mlx_extraction.py`
  - `scripts/ingest_extraction_responses.py`
  - `scripts/review_extraction_quality.py`
  - `scripts/review_and_ingest_extractions.py`
  - `data/structural-analogy/runs/abstract_extraction-20260326T003830Z/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-20260326T003830Z/ingest_summary.json`
  - `data/structural-analogy/runs/abstract_extraction-20260326T003830Z/gate_summary.json`
  - `data/structural-analogy/runs/abstract_extraction-20260326T003830Z/responses.mlx.sample.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-20260326T003830Z/responses.mlx.sample.quality.json`
  - `data/structural-analogy/runs/abstract_extraction-20260326T003830Z/responses.pass.sample.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-20260326T003830Z/responses.pass.sample.quality.json`
  - `data/structural-analogy/runs/abstract_extraction_v2-smoke/responses.jsonl`
  - `data/structural-analogy/runs/abstract_extraction_v2-smoke/responses.quality.json`
  - `data/structural-analogy/runs/abstract_extraction-v3-pilot10/summary.json`
  - `data/structural-analogy/runs/abstract_extraction-v3-pilot10/responses.first10.jsonl`
  - `data/structural-analogy/runs/abstract_extraction-v3-pilot10/responses.first10.quality.json`
  - `data/structural-analogy/runs/abstract_extraction_v3-smoke/responses.jsonl`
  - `data/structural-analogy/runs/abstract_extraction_v3-smoke/responses.quality.json`

Deliverables:

- prompt templates
- batch runner
- validation logic
- raw extraction outputs

Success criteria:

- 200-paper pilot yields stable structured records

## Phase 4. Normalization and fingerprinting

Status: `planned`
Owner: `unassigned`
Exit criteria status: `not_started`
Comments:

- This phase will determine whether retrieval is actually non-obvious or just semantically nearby.

Deliverables:

- enum mappers
- fingerprint builder
- ontology QA scripts

Success criteria:

- retrieval by fingerprint returns obviously related structural cases even across different vocabularies

## Phase 5. Embeddings and graph

Status: `planned`
Owner: `unassigned`
Exit criteria status: `not_started`
Comments:

- Need separate embeddings for abstract, mechanism summary, and serialized fingerprint.

Deliverables:

- local embedding pipeline
- graph edges
- basic exploration notebook or CLI

Success criteria:

- can retrieve nearest fit, far analogs, and bridge papers on demand

## Phase 6. Scoring and review queue

Status: `planned`
Owner: `unassigned`
Exit criteria status: `not_started`
Comments:

- Scoring should over-weight novelty with executable fit, not generic relevance.

Deliverables:

- ranking function
- candidate generation job
- review packet template

Success criteria:

- top 20 candidates feel non-obvious and executable rather than generic

## Phase 7. Strategy handoff

Status: `planned`
Owner: `unassigned`
Exit criteria status: `not_started`
Comments:

- Output should become concrete strategy briefs, not just literature summaries.

Deliverables:

- top 10 mechanism briefs
- mapped executor concepts
- open questions for data and backtest design

Success criteria:

- at least 3 candidate strategy families worth prototyping in `tradecore`

---

## Local-First Execution Plan

This should be built entirely locally unless quality proves unacceptable.

Recommended local-first stack:

- Python for pipeline code
- DuckDB or SQLite for storage
- local PDF extraction tools
- local embeddings
- local instruct model for first-pass extraction

Recommended operating mode:

1. run embeddings and abstract-level extraction over the full corpus
2. shortlist candidate clusters and far analogs
3. run deeper full-text extraction only on shortlisted papers

This avoids wasting local inference budget on weak candidates.

---

## Risks

Main risks:

- bad PDF text extraction
- extraction drift across papers and domains
- ontology bloat
- overfitting to semantic similarity instead of structural analogy
- generating “interesting but not executable” candidates

Mitigations:

- section-aware extraction
- two-pass extraction + normalization
- controlled vocabularies
- `tradecore_fit` as a first-class score
- manual review packets before any strategy claims

---

## Immediate Next Steps

1. Retire the remaining narrower `high_fit_without_specific_why_missed` cases exposed by the `v24` `50`-paper rerun, especially `2206.05410` and `1310.6873`.
2. Re-run the larger `50`-paper slice and confirm the schema-aware gate clears at `0/50` blocking.
3. If the larger pass clears, run the first `50`-paper gate-and-ingest attempt.
4. Harden the extraction schema against the first real pilot-batch examples.
5. Harden the fingerprint ontology against adjacent-domain and pilot coverage gaps.
6. Evaluate retrieval quality on:
   - nearest fit
   - far analog
   - bridge papers
7. Expand to full-text only after the pilot shows useful candidates.

---

## Additional Context (For AIs and Deep Dives)

### Working Definitions

- `structural analogy`: two papers describe the same trade geometry or market mechanism even if domain language is unrelated
- `diamond in the rough`: a mechanism with high structural fit and low surface obviousness
- `tradecore fit`: whether the mechanism can plausibly be expressed by the current or near-future executor primitives

### Draft Minimal Extraction Schema

```json
{
  "paper_id": "string",
  "mechanism_name": "string",
  "mechanism_summary": "string",
  "original_market_domain": "string",
  "instrument_type": ["string"],
  "edge_source": ["string"],
  "execution_style": ["string"],
  "holding_horizon": "intraday|multi_day|event_resolution|other",
  "required_market_conditions": ["string"],
  "main_failure_modes": ["string"],
  "evidence_strength": "weak|medium|strong",
  "prediction_market_portability": "low|medium|high",
  "novel_market_portability": "low|medium|high",
  "tradecore_fit": "low|medium|high",
  "likely_crowding": "low|medium|high",
  "why_missed": ["string"]
}
```

### Draft Minimal Structural Fingerprint

```json
{
  "topology": "two_leg_parity|n_leg_basket|term_structure|implication_graph|queue_value_mm|other",
  "market_structure": ["thin_book", "fragmented", "discrete_ticks", "reward_incentivized", "asynchronous"],
  "mispricing_source": ["logical_inconsistency", "stale_quotes", "inventory_pressure", "reward_incentives", "settlement_friction"],
  "execution_pattern": ["maker_anchor", "parallel_fok", "sequential_fok", "quote_ladder", "recovery_gtc"],
  "participant_pressure": ["retail_flow", "maker_incentives", "forced_hedging", "latency_sensitive"],
  "time_structure": ["event_time", "expiry_sensitive", "sequential_revelation", "resolution_dependent"],
  "risk_controls": ["forced_hedge", "inventory_cap", "stale_data_guard", "venue_health_gate"],
  "transfer_targets": ["prediction_markets", "multi_outcome_events", "cross_venue_yes_no", "reward_mm"],
  "tradecore_fit_tags": ["anchor_hedge", "basket_completion", "fok_window", "reward_mm"]
}
```

### Retrieval Queries To Support

- “Find structurally similar papers to sum-to-one baskets, but outside prediction-market and q-fin vocabulary.”
- “Find papers with reward-incentive and queue-preservation structure that could inform reward-MM.”
- “Find bridge papers between auction theory and event-market microstructure.”
- “Find implication-graph setups that could map onto linked Kalshi/Polymarket events.”

### Success Test For The Engine

The engine is working if it can produce candidate mechanisms that satisfy all of:

- not obvious from direct q-fin nearest neighbors
- understandable as a concrete market mechanism
- plausibly portable into novel event markets
- mappable onto `tradecore` strategy primitives
- worth a real prototype discussion

### Session Artifacts

- corpus harvest scripts in this repo:
  - `scripts/harvest_arxiv_qfin.py`
  - `scripts/download_arxiv_pdfs.py`
- active PDF download job:
  - `logs/qfin_download.log`
  - `logs/qfin_download.pid`
- current reference execution surface lives in sibling repo:
  - `../tradecore/docs/executors/`
- phase 1 schema artifacts in this repo:
  - `schemas/extraction.schema.json`
  - `schemas/fingerprint.schema.json`
  - `schemas/normalization_vocab.json`
  - `schemas/examples/extraction.example.json`
  - `schemas/examples/fingerprint.example.json`
  - `scripts/validate_schema_examples.py`
  - `sql/paperview_schema.sql`
  - `scripts/init_local_store.py`
  - `scripts/load_metadata_store.py`
  - `scripts/create_pilot_batch.py`
  - `prompts/abstract-extraction-v1.md`
  - `prompts/abstract-extraction-v2.md`
  - `scripts/create_extraction_run.py`
  - `scripts/run_local_mlx_extraction.py`
  - `scripts/ingest_extraction_responses.py`

### Update Protocol

When using this doc as a living tracker:

1. Update `Status`, `Current Focus`, and `Progress Board`.
2. Append new decisions to `Decision Log`.
3. Add dated bullets to `Working Notes`.
4. Update the phase block for the active phase:
   - `Status`
   - `Owner`
   - `Exit criteria status`
   - `Comments`
5. Do not delete old notes unless they are factually wrong; prefer superseding them.
