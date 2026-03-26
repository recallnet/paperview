# arXiv q-fin Harvester

This repo contains a small set of Python scripts for building a local `q-fin` corpus from arXiv.

## Canonical Model

The repo now treats `mechanism_instance` as the canonical storage and reasoning
unit for the structural analogy engine.

- One paper may map to `0..N` mechanism instances.
- `paper_extractions` is still used by the current abstract-first ingest path,
  but only as a transitional staging table.
- The active extraction contract now requires `insight_type` plus explicit
  fragility, capacity, failure-regime, and negative-transfer fields so
  promising candidates stay falsifiable.
- The adjacent-literature seeding surface now lives in checked-in registries
  under `configs/`, with explicit active-family versus holdout split policy.
- Downstream retrieval, benchmarking, transfer review, and candidate-family
  work should target `mechanism_instances`, `mechanism_evidence_spans`,
  `transfer_hypotheses`, `candidate_families`, `analyst_labels`, and
  `benchmark_pairs`.

The discovery source is the DOAPR arXiv entry:

- <https://doapr.coar-repositories.org/repositories/arxiv/>

That page exposes arXiv's OAI-PMH endpoint. The scripts use arXiv's current HTTPS base URL:

- <https://oaipmh.arxiv.org/oai>

## What the scripts do

1. `scripts/harvest_arxiv_qfin.py`
   Harvests every record in the `q-fin` OAI set and writes:
   - `data/arxiv-qfin/metadata.jsonl`
   - `data/arxiv-qfin/metadata.csv`
   - `data/arxiv-qfin/ids.txt`
   - `data/arxiv-qfin/harvest_checkpoint.json` while an in-progress run is active

2. `scripts/download_arxiv_pdfs.py`
   Reads `ids.txt` and downloads PDFs into `data/arxiv-qfin/pdfs/`, with a resumable manifest and failure log.

3. `scripts/corpus_status.py`
   Reports corpus completeness and downloader status from local artifacts:
   - expected paper count
   - downloaded count
   - failure count
   - downloader PID/running state
   - recent log lines

4. `scripts/launch_qfin_download.py`
   Launches the PDF downloader as a detached background process and writes:
   - `logs/qfin_download.pid`
   - `logs/qfin_download.launch.json`
   - `logs/qfin_download.log`

5. `scripts/corpus_inventory.py`
   Builds exact completeness artifacts from local corpus state:
   - `data/arxiv-qfin/inventory/summary.json`
   - `data/arxiv-qfin/inventory/missing_ids.txt`
   - `data/arxiv-qfin/inventory/downloaded_ids.txt`
   - `data/arxiv-qfin/inventory/failed_ids.txt`

6. `scripts/reconcile_failures.py`
   Normalizes the raw failures log into a canonical latest-per-ID failure view:
   - `data/arxiv-qfin/inventory/failures_canonical.jsonl`
   - `data/arxiv-qfin/inventory/failures_summary.json`
   - `data/arxiv-qfin/inventory/failed_ids_canonical.txt`
   - `data/arxiv-qfin/inventory/failed_ids_permanent.txt`

7. `scripts/retry_failures.py`
   Builds a retry queue from canonical retryable failures and can optionally run a focused retry pass through the existing downloader.

8. `scripts/run_qfin_pipeline.py`
   Runs the full corpus pull pipeline for a corpus directory:
   - main downloader pass
   - inventory refresh
   - retry queue materialization
   - bounded retryable-failure pass
   - final inventory refresh

9. `scripts/corpus_readiness_report.py`
   Builds a Phase 0 readiness artifact from local corpus state:
   - `reports/corpus-readiness/latest.json`
   - `reports/corpus-readiness/latest.md`

## Why OAI-PMH first

`q-fin` is exposed as an arXiv OAI set, so this is the cleanest way to enumerate the full category without scraping the website.

For a very large full-text pull, arXiv's own docs point to bulk full-text access through S3 and Kaggle. If you need the entire corpus at scale, that is the better long-run path than hitting `arxiv.org/pdf/...` for every paper.

## Usage

Harvest all `q-fin` metadata:

```bash
python3 scripts/harvest_arxiv_qfin.py
```

Resume an interrupted harvest:

```bash
python3 scripts/harvest_arxiv_qfin.py --resume
```

Harvest a smaller test slice:

```bash
python3 scripts/harvest_arxiv_qfin.py --from-date 2026-03-01 --max-records 25
```

Download a small sample of PDFs:

```bash
python3 scripts/download_arxiv_pdfs.py \
  --metadata-jsonl data/arxiv-qfin/metadata.jsonl \
  --workers 4 \
  --delay-seconds 1.0 \
  --max-downloads 10 \
  --skip-existing
```

Download the full harvested ID list:

```bash
python3 scripts/download_arxiv_pdfs.py \
  --metadata-jsonl data/arxiv-qfin/metadata.jsonl \
  --workers 4 \
  --delay-seconds 1.0 \
  --skip-existing
```

Check corpus readiness / downloader status:

```bash
python3 scripts/corpus_status.py
```

Launch or relaunch the background downloader:

```bash
npm run corpus:launch
```

Build a completeness inventory:

```bash
npm run corpus:inventory
```

Materialize retryable failure IDs:

```bash
npm run corpus:retryable-failures
```

Run the full pull pipeline in-process:

```bash
npm run corpus:run-pipeline
```

Launch the full pull pipeline in the background:

```bash
npm run corpus:launch:pipeline
```

Build the latest readiness report:

```bash
npm run corpus:readiness
```

Initialize the canonical local store for the extraction pipeline:

```bash
npm run store:init
```

Load harvested metadata into the canonical store:

```bash
npm run store:load-metadata
```

The loader is idempotent: reruns update existing paper rows in place and refresh
local PDF presence in `ingest_status` / `pdf_path`.

For adjacent corpora, stamp the canonical family and split on ingest:

```bash
python3 scripts/load_metadata_store.py \
  --metadata-jsonl <adjacent.jsonl> \
  --pdf-dir <adjacent-pdfs> \
  --source-corpus adjacent-defi-amm \
  --literature-family defi_amm_onchain_market_design \
  --evaluation-split tuning
```

Create the deterministic abstract-first pilot batch:

```bash
npm run pilot:create
```

Build a mixed-family pilot while excluding holdout rows:

```bash
python3 scripts/create_pilot_batch.py \
  --db-path data/structural-analogy/paperview.sqlite3 \
  --source-corpus all \
  --literature-families q_fin,defi_amm_onchain_market_design,electricity_power_markets \
  --exclude-evaluation-split holdout \
  --batch-name abstract-pilot-mixed-v1
```

Prepare an abstract-only extraction run from that pilot batch:

```bash
npm run extract:prepare
```

Prepare a capped benchmark slice directly from the active prompt file instead of
copying old request artifacts forward:

```bash
python3 scripts/create_extraction_run.py \
  --prompt-path prompts/abstract-extraction-v8.md \
  --prompt-version abstract-extraction-v8 \
  --run-id abstract_extraction-v8-pilot25 \
  --model-name mlx-community/Qwen2.5-3B-Instruct-4bit \
  --max-requests 25
```

Run a local MLX-backed extraction pass over prepared requests:

```bash
npm run extract:run-mlx -- --requests-path <requests.jsonl> --responses-path <responses.jsonl> --max-requests 1
```

Prompt iteration is still active. The strongest widened-slice batch prompt is
now the v10 line: the fixed 10-paper benchmark is clean under the schema-aware
gate, and the widened 25-paper v10 rerun is also clean at `0/25` blocking.
Prompt v9 remains a useful targeted experiment for the `2412.03618` blocker,
but v10 is the first merged prompt that preserves batch stability and clears
the widened slice. The first beyond-benchmark gate-and-ingest pass has also now
completed successfully on that clean v10 25-paper batch. The first larger
50-paper v10 review slice is not yet clean, so larger-scale extraction still
needs another blocker-retirement pass before ingestion. The first of those
larger-slice blocker classes, `2510.07444`, now passes in targeted smoke-test
form under the v12 prompt. The second larger-slice blocker class, `2210.15329`,
now also passes in targeted smoke-test form under the v13 prompt after adding a
climate-transition investment-fund collapse rule and an explicit full-key
requirement for conservative outputs. The third larger-slice blocker class,
`2511.17963`, now also passes in targeted smoke-test form under the v14 prompt
after adding a hybrid forecasting-plus-RL portfolio-optimization collapse rule.
However, the first full v14 `50`-paper verification rerun is still not clean:
it lands at `4/50` blocking, including a regression on `2510.07444` and three
rows that still drop required `mechanism_name` under conservative collapse.
That debt/loan regression is now fixed again in targeted smoke-test form under
the v15 prompt, which forces generic loan-VaR papers to collapse fully to
all-`other` execution and edge fields.
The representative missing-`mechanism_name` collapse bug is also now fixed in
targeted smoke-test form under the v16 prompt, which forces conservative
all-`other` rows to still derive `mechanism_name` and `mechanism_summary` from
the paper title/topic. That fix also clears the two remaining cond-mat
missing-key cases structurally, although one still uses placeholder
`mechanism_name = "None"`, so the next issue is semantic quality rather than
schema completeness. The reviewer now blocks placeholder mechanism names, and
that stricter rule correctly catches the `cond-mat/0108452` output. Prompt v17
adds an explicit no-placeholder rule, and prompt v18 now fixes that scaling-
paper case in targeted smoke-test form by producing a concrete title-derived
mechanism name. The first full v18 `50`-paper verification rerun is also a
real improvement over v14: it is down to `2` blocking rows and `1` warning.

Ingest validated extraction responses back into SQLite:

```bash
npm run extract:ingest -- --run-id <run_id> --responses-path <responses.jsonl>
```

Today this command persists validated model output into transitional
`paper_extractions` rows. That keeps the current extraction workflow usable
while the mechanism-first persistence refactor is completed.

The validated extraction payload now requires:

- `insight_type`
- `required_assumptions`
- `assumption_violations`
- `fragility_flags`
- `capacity_constraints`
- `failure_regimes`
- `negative_transfer_rationale`

The reviewer also blocks promising candidates that lack specific blocker
context, so extraction outputs cannot stay “interesting” but unfalsifiable.

Review extraction quality before scaling a run:

```bash
npm run extract:review-quality -- --responses-path <responses.jsonl>
```

To fail a CI step or rollout on blocking findings:

```bash
npm run extract:review-quality -- --responses-path <responses.jsonl> --fail-on-blocking
```

To enforce the gate and ingest only passing outputs:

```bash
npm run extract:gate-and-ingest -- --run-id <run_id> --responses-path <responses.jsonl>
```

Validate the checked-in Phase 1 schema artifacts:

```bash
npm run schemas:validate
```

Materialize the checked-in adjacent seeding plan and reserved holdout slice:

```bash
python3 scripts/materialize_adjacent_seeding_plan.py \
  --output-dir data/structural-analogy/adjacent-seeding/plan-v1
```

## Notes

- The metadata harvester follows OAI `resumptionToken`s automatically.
- The metadata harvester now streams CSV/JSONL writes and can resume from `harvest_checkpoint.json`.
- The downloader stores files as `<arxiv_id>.pdf`, with `/` replaced by `_` for old-style IDs.
- The downloader appends successful results to `manifest.jsonl` and failed attempts to `failures.jsonl`.
- PDF `404` responses are treated as permanent no-PDF cases and logged immediately with `failure_type=permanent` instead of retrying all attempts.
- Exhausted `5xx` responses are logged as `failure_type=retryable_http_5xx` so they remain distinguishable from permanent no-PDF cases.
- The downloader skips work already present in `manifest.jsonl`, and `--skip-existing` also treats on-disk PDFs as completed.
- `scripts/corpus_status.py` is the quickest way to confirm whether a background pull is still alive and how far it got. It now refreshes the inventory summary automatically when the manifest has advanced.
- `scripts/launch_qfin_download.py` is the canonical way to start the background pull from this repo.
- `scripts/corpus_inventory.py` is the canonical way to enumerate exact missing/downloaded/failed IDs, and it now reconciles failure-log duplicates into a canonical latest-per-ID view.
- `scripts/reconcile_failures.py` can also be run directly when you want failure-log normalization without a full inventory refresh.
- `scripts/retry_failures.py` is the canonical way to build and optionally re-run the current retryable failure set.
- `scripts/run_qfin_pipeline.py` is the canonical automated path when you want the main pull followed by a bounded retryable-failure pass in one run.
- `scripts/corpus_readiness_report.py` is the canonical Phase 0 review artifact when you want one file summarizing downloader health, completeness, and failure classes.
- `scripts/init_local_store.py` is the canonical way to initialize the local SQLite store at `data/structural-analogy/paperview.sqlite3`.
- `scripts/load_metadata_store.py` is the canonical way to populate the SQLite `papers` table from harvested metadata and current local PDF state.
- `scripts/create_pilot_batch.py` is the canonical way to materialize a deterministic pilot batch under `data/structural-analogy/pilots/`.
- `scripts/create_extraction_run.py` is the canonical way to register an abstract-extraction run in SQLite and export prompt-ready requests under `data/structural-analogy/runs/`.
  Use `--max-requests` to regenerate capped benchmark slices from the actual prompt file; do not clone older `requests.jsonl` files forward when comparing prompt versions.
- `scripts/run_local_mlx_extraction.py` is the first local execution backend for prepared abstract-extraction runs on Apple Silicon via `mlx-lm`.
- `scripts/ingest_extraction_responses.py` is the canonical way to validate model outputs against the extraction schema and persist them to `paper_extractions`.
- `scripts/review_extraction_quality.py` is the canonical pre-scale quality gate for semantically wrong but schema-valid outputs.
  It now classifies findings into `blocking` vs `warning` and can exit non-zero on blocking results.
- `scripts/review_and_ingest_extractions.py` is the canonical policy command when a run should only ingest after passing the quality gate.
- `prompts/abstract-extraction-v10.md` is the current active widened-slice prompt iteration.
- `prompts/abstract-extraction-v8.md` is the previous strongest batch-stable widened prompt baseline.
- `prompts/abstract-extraction-v9.md` is a targeted blocker-fix experiment for `2412.03618`, not yet the active batch prompt.
- `abstract_extraction-v10-pilot25` is the first beyond-benchmark run that has both passed the gate and been ingested into SQLite.
- `abstract_extraction-v10-pilot50` is the first larger review slice; it is a diagnosis set for new blocker classes, not an ingest candidate yet.
- `prompts/abstract-extraction-v12.md` is the current targeted fix branch for the first larger-slice blocker class (`2510.07444` debt/loan portfolio risk).
- `prompts/abstract-extraction-v13.md` is the current targeted fix branch for the second larger-slice blocker class (`2210.15329` climate-transition / mixed-fund exposure risk).
- `prompts/abstract-extraction-v14.md` is the current targeted fix branch for the third larger-slice blocker class (`2511.17963` hybrid forecasting-plus-RL portfolio optimization).
- `prompts/abstract-extraction-v15.md` is the current targeted fix branch for the reintroduced debt/loan regression on `2510.07444` in the merged `50`-paper batch line.
- `prompts/abstract-extraction-v16.md` is the current targeted fix branch for the representative missing-`mechanism_name` conservative-collapse bug (`2205.01524`).
- `prompts/abstract-extraction-v17.md` introduced the explicit no-placeholder rule that the reviewer now enforces.
- `prompts/abstract-extraction-v18.md` is the current targeted fix branch for the placeholder-name semantic quality bug on `cond-mat/0108452`.
- `prompts/abstract-extraction-v19.md` is the current targeted fix branch for the market-making schema-alignment blocker on `2206.05410`.
- `prompts/abstract-extraction-v20.md` is the failed first rule-only branch for the venture-capital domain drift on `2103.11557`; it is kept as a comparison artifact.
- `prompts/abstract-extraction-v21.md` is the current targeted fix branch for the venture-capital exit-timing domain drift on `2103.11557`.
- `prompts/abstract-extraction-v22.md` is the current merged larger-batch candidate, built from the stable `v18` surface plus the `v19` and `v21` fixes.
- `prompts/abstract-extraction-v23.md` is the current targeted fix branch for the last remaining larger-batch blocker on `2002.02583`, where high-fit FX linked-market output still needed specific `why_missed` reasons.
- `prompts/abstract-extraction-v24.md` is the narrower merge candidate: it keeps the FX exemplar from `v23` but drops the broad global high-fit rule that destabilized the full `v23` batch.
- `prompts/abstract-extraction-v25.md` is the targeted off-domain fix branch for political-science measurement and AI ethics / moral-agent papers that were still drifting into high-fit larger-batch outputs.
- `abstract_extraction-v16-missing-name-condmat-smoke` verifies that the two remaining cond-mat missing-key cases now pass structurally under v16, but `cond-mat/0108452` still needs a better non-placeholder mechanism name.
- `abstract_extraction-v18-pilot50` is the current larger-batch verification baseline; it improves the batch to `2/50` blocking and `1/50` warning.
- `data/structural-analogy/runs/abstract_extraction-v18-pilot50/responses.first50.quality.v2.json` is the refreshed reviewer output for the same batch after explicit DeFi / DAO / blockchain cues were added to the reviewer; the warning count drops to `0`.
- `abstract_extraction-v19-mm-smoke` verifies that `2206.05410` now keeps `inventory_pressure` in `edge_source`, keeps `required_market_conditions` schema-valid, and passes the schema-aware gate.
- `abstract_extraction-v21-vc-smoke` verifies that `2103.11557` now collapses cleanly to `original_market_domain = other` and passes the schema-aware gate.
- `abstract_extraction-v22-pilot50` is the current strongest larger-batch rerun: it improves the `50`-paper slice to `1/50` blocking and `0/50` warning.
- `abstract_extraction-v23-fx-smoke` verifies that `2002.02583` now keeps its high-fit linked-market framing while using specific `why_missed` reasons instead of `other`.
- `abstract_extraction-v23-pilot50` is a failed merged rerun: it regresses to `9/50` blocking, so `v23` should remain a targeted branch rather than the new active batch prompt.
- `abstract_extraction-v24-fx-smoke` verifies that the narrower `v24` merge preserves the `2002.02583` fix without importing the broad global `why_missed` rule from `v23`.
- `abstract_extraction-v24-pilot50` is a partial recovery: it improves the larger batch from `9/50` blocking on `v23` to `4/50` blocking, but it is still not gate-clean enough to ingest.
- `abstract_extraction-v25-offdomain-smoke` verifies that the two generic off-domain overreach papers from the `v24` blocker set (`2301.11084` and `2305.11519`) now collapse cleanly to low-fit, low-portability all-`other` outputs.
- `abstract_extraction-v14-pilot50` is the older merged `50`-paper verification rerun and remains a comparison artifact for the larger blocker set it exposed.
- Phase 1 schema and ontology artifacts now live under `schemas/`, with bundled examples validated by `scripts/validate_schema_examples.py`.
- Both scripts use only the Python standard library.
- Default downloader settings are bounded-concurrency, not max-throughput. If arXiv starts pushing back, lower `--workers` or raise `--delay-seconds`.
