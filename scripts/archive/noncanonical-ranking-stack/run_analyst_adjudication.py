#!/usr/bin/env python3

import argparse
import json
import math
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

STACK_DIR = Path(__file__).resolve().parent
if str(STACK_DIR) not in sys.path:
    # @context requirement -- the archived ranking stack shares local modules
    # by bare import name, so the archive has to restore that path explicitly
    # after moving the files out of the active root.
    sys.path.insert(0, str(STACK_DIR))

import score_mechanism_exposure as exposure_scoring


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_SQL_PATH = ROOT / "sql" / "paperview_schema.sql"
DEFAULT_MINING_VERSION = "c11-queryless-v1"
DEFAULT_SCORE_VERSION = "c09-exposure-v1"
DEFAULT_RUN_KIND = "analyst_adjudication"
BOOLEAN_LABEL_KINDS = (
    "accept",
    "structurally_relevant",
    "non_obvious",
    "genuinely_new",
    "worth_strategy_brief",
)
TEXT_REASON_FIELDS = {
    "interesting_reasons": "interesting_reason",
    "weak_reasons": "weakness_reason",
}
POSITIVE_VALUES = {"yes", "true", "1", "accept", "accepted", "high", "worth_it"}
NEGATIVE_VALUES = {"no", "false", "0", "reject", "rejected", "low", "not_worth_it"}
LABEL_WEIGHTS = {
    "accept": 0.35,
    "structurally_relevant": 0.20,
    "non_obvious": 0.15,
    "genuinely_new": 0.15,
    "worth_strategy_brief": 0.15,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Persist analyst adjudications and learn reranker weight updates."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--schema-sql-path",
        default=str(DEFAULT_SCHEMA_SQL_PATH),
        help="Path to the SQL schema to apply before adjudication.",
    )
    parser.add_argument(
        "--queryless-run-id",
        required=True,
        help="Queryless mining run id produced by mine_queryless_candidates.py.",
    )
    parser.add_argument(
        "--labels-path",
        required=True,
        help="Path to a JSONL file of analyst adjudications.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit analyst adjudication run id.",
    )
    parser.add_argument(
        "--created-by",
        default="analyst",
        help="Name or handle to persist as the label author.",
    )
    parser.add_argument(
        "--mining-version",
        default=DEFAULT_MINING_VERSION,
        help="Queryless mining contract version to read.",
    )
    parser.add_argument(
        "--score-version",
        default=DEFAULT_SCORE_VERSION,
        help="Exposure score version to refresh after labels are written.",
    )
    parser.add_argument(
        "--skip-exposure-refresh",
        action="store_true",
        help="Skip the c09 exposure refresh when only reranker labels are needed.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def clamp(value):
    return max(0.0, min(1.0, value))


def sigmoid(value):
    if value >= 0:
        exp_value = math.exp(-value)
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def parse_json_lines(path: Path):
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        materialized = line.strip()
        if not materialized:
            continue
        try:
            records.append(json.loads(materialized))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
    return records


def normalize_label_value(value):
    if isinstance(value, bool):
        return "yes" if value else "no"
    materialized = str(value or "").strip().lower()
    if materialized in POSITIVE_VALUES:
        return "yes"
    if materialized in NEGATIVE_VALUES:
        return "no"
    if materialized:
        return materialized
    return ""


def parse_bool_label(value):
    normalized = normalize_label_value(value)
    if normalized == "yes":
        return 1
    if normalized == "no":
        return 0
    return None


def ensure_store_contract(connection, schema_sql_path: Path):
    connection.executescript(schema_sql_path.read_text(encoding="utf-8"))


def ensure_run(connection, run_id: str | None, args):
    resolved_run_id = run_id or (
        f"{DEFAULT_RUN_KIND}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    config = {
        "queryless_run_id": args.queryless_run_id,
        "labels_path": str(Path(args.labels_path).resolve()),
        "mining_version": args.mining_version,
        "score_version": args.score_version,
    }
    existing = connection.execute(
        "SELECT run_id FROM extraction_runs WHERE run_id = ?",
        (resolved_run_id,),
    ).fetchone()
    if existing is None:
        connection.execute(
            """
            INSERT INTO extraction_runs (
              run_id,
              run_kind,
              model_name,
              prompt_version,
              config_json,
              started_at,
              run_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_run_id,
                DEFAULT_RUN_KIND,
                args.queryless_run_id,
                args.mining_version,
                json.dumps(config, sort_keys=True),
                now_utc(),
                "running",
            ),
        )
    else:
        connection.execute(
            """
            UPDATE extraction_runs
            SET run_kind = ?,
                model_name = ?,
                prompt_version = ?,
                config_json = ?,
                run_status = ?,
                completed_at = NULL
            WHERE run_id = ?
            """,
            (
                DEFAULT_RUN_KIND,
                args.queryless_run_id,
                args.mining_version,
                json.dumps(config, sort_keys=True),
                "running",
                resolved_run_id,
            ),
        )
    return resolved_run_id


def load_queryless_hits(connection, queryless_run_id: str, mining_version: str):
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          qch.queryless_candidate_hit_id,
          qch.run_id,
          qch.mining_mode,
          qch.source_mechanism_instance_id,
          qch.candidate_mechanism_instance_id,
          qch.source_paper_id,
          qch.candidate_paper_id,
          qch.source_literature_family,
          qch.candidate_literature_family,
          qch.source_evaluation_split,
          qch.candidate_evaluation_split,
          qch.rank_within_source,
          qch.is_cross_family,
          qch.structural_similarity_score,
          qch.lexical_distance_score,
          qch.transfer_plausibility_score,
          qch.blocker_penalty_score,
          qch.reranker_score,
          qch.rationale_json,
          bp.benchmark_pair_id
        FROM queryless_candidate_hits qch
        LEFT JOIN benchmark_pairs bp
          ON bp.source_mechanism_instance_id = qch.source_mechanism_instance_id
         AND bp.candidate_mechanism_instance_id = qch.candidate_mechanism_instance_id
        WHERE qch.run_id = ?
          AND qch.mining_version = ?
        ORDER BY qch.queryless_candidate_hit_id
        """,
        (queryless_run_id, mining_version),
    ).fetchall()
    by_id = {}
    by_signature = {}
    for row in rows:
        record = dict(row)
        by_id[row["queryless_candidate_hit_id"]] = record
        by_signature[
            (
                row["source_mechanism_instance_id"],
                row["candidate_mechanism_instance_id"],
                row["mining_mode"],
            )
        ] = record
    return by_id, by_signature


def resolve_hit(record, hits_by_id, hits_by_signature):
    if record.get("queryless_candidate_hit_id") is not None:
        hit = hits_by_id.get(int(record["queryless_candidate_hit_id"]))
        if hit is None:
            raise SystemExit(
                f"unknown queryless_candidate_hit_id {record['queryless_candidate_hit_id']}"
            )
        return hit
    signature = (
        record.get("source_mechanism_instance_id"),
        record.get("candidate_mechanism_instance_id"),
        record.get("mining_mode"),
    )
    if None in signature:
        raise SystemExit(
            "each label row must include `queryless_candidate_hit_id` or "
            "`source_mechanism_instance_id`, `candidate_mechanism_instance_id`, and `mining_mode`"
        )
    hit = hits_by_signature.get(signature)
    if hit is None:
        raise SystemExit(f"no queryless hit found for signature {signature}")
    return hit


def build_label_rows(records, hits_by_id, hits_by_signature, created_by: str):
    label_rows = []
    labeled_hit_ids = set()
    for record in records:
        hit = resolve_hit(record, hits_by_id, hits_by_signature)
        labeled_hit_ids.add(hit["queryless_candidate_hit_id"])
        base_notes = record.get("notes")
        for label_kind in BOOLEAN_LABEL_KINDS:
            if label_kind not in record:
                continue
            normalized_value = normalize_label_value(record[label_kind])
            if not normalized_value:
                continue
            label_rows.append(
                {
                    "mechanism_instance_id": hit["candidate_mechanism_instance_id"],
                    "benchmark_pair_id": hit["benchmark_pair_id"],
                    "queryless_candidate_hit_id": hit["queryless_candidate_hit_id"],
                    "label_kind": label_kind,
                    "label_value": normalized_value,
                    "notes": base_notes,
                    "created_by": created_by,
                }
            )
        for field_name, label_kind in TEXT_REASON_FIELDS.items():
            for reason in record.get(field_name, []) or []:
                materialized = str(reason or "").strip()
                if not materialized:
                    continue
                label_rows.append(
                    {
                        "mechanism_instance_id": hit["candidate_mechanism_instance_id"],
                        "benchmark_pair_id": hit["benchmark_pair_id"],
                        "queryless_candidate_hit_id": hit["queryless_candidate_hit_id"],
                        "label_kind": label_kind,
                        "label_value": materialized.lower().replace(" ", "_"),
                        "notes": materialized,
                        "created_by": created_by,
                    }
                )
    return label_rows, labeled_hit_ids


def persist_labels(connection, label_rows):
    inserted = 0
    for row in label_rows:
        connection.execute(
            """
            INSERT INTO analyst_labels (
              mechanism_instance_id,
              benchmark_pair_id,
              queryless_candidate_hit_id,
              label_kind,
              label_value,
              notes,
              created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["mechanism_instance_id"],
                row["benchmark_pair_id"],
                row["queryless_candidate_hit_id"],
                row["label_kind"],
                row["label_value"],
                row["notes"],
                row["created_by"],
            ),
        )
        inserted += 1
    return inserted


def load_adjudicated_hits(connection):
    connection.row_factory = sqlite3.Row
    hits = {}
    for row in connection.execute(
        """
        SELECT
          qch.queryless_candidate_hit_id,
          qch.run_id AS queryless_run_id,
          qch.mining_version,
          qch.mining_mode,
          qch.source_mechanism_instance_id,
          qch.candidate_mechanism_instance_id,
          qch.source_evaluation_split,
          qch.candidate_evaluation_split,
          qch.is_cross_family,
          qch.structural_similarity_score,
          qch.lexical_distance_score,
          qch.transfer_plausibility_score,
          qch.blocker_penalty_score,
          qch.reranker_score
        FROM queryless_candidate_hits qch
        """
    ):
        hits[row["queryless_candidate_hit_id"]] = dict(row)
    labels_by_hit = defaultdict(dict)
    reasons_by_hit = defaultdict(lambda: {"interesting_reason_count": 0, "weakness_reason_count": 0})
    for row in connection.execute(
        """
        SELECT queryless_candidate_hit_id, label_kind, label_value
        FROM analyst_labels
        WHERE queryless_candidate_hit_id IS NOT NULL
        """
    ):
        hit_id = row["queryless_candidate_hit_id"]
        label_kind = row["label_kind"]
        label_value = row["label_value"]
        if label_kind in BOOLEAN_LABEL_KINDS:
            parsed_value = parse_bool_label(label_value)
            if parsed_value is not None:
                labels_by_hit[hit_id][label_kind] = parsed_value
        elif label_kind == "interesting_reason":
            reasons_by_hit[hit_id]["interesting_reason_count"] += 1
        elif label_kind == "weakness_reason":
            reasons_by_hit[hit_id]["weakness_reason_count"] += 1

    training_rows = []
    for hit_id, hit in hits.items():
        labels = labels_by_hit.get(hit_id, {})
        weighted_total = 0.0
        weight_mass = 0.0
        for label_kind, label_weight in LABEL_WEIGHTS.items():
            label_value = labels.get(label_kind)
            if label_value is None:
                continue
            weighted_total += label_weight * label_value
            weight_mass += label_weight
        if weight_mass == 0.0:
            continue
        aggregate_label = weighted_total / weight_mass
        if 0.4 < aggregate_label < 0.6:
            continue
        training_rows.append(
            {
                **hit,
                "label": 1 if aggregate_label >= 0.6 else 0,
                "aggregate_label": aggregate_label,
                "interesting_reason_count": reasons_by_hit[hit_id]["interesting_reason_count"],
                "weakness_reason_count": reasons_by_hit[hit_id]["weakness_reason_count"],
            }
        )
    return hits, training_rows


def feature_vector(hit):
    return {
        "structural_similarity_score": hit["structural_similarity_score"],
        "lexical_distance_score": hit["lexical_distance_score"],
        "transfer_plausibility_score": hit["transfer_plausibility_score"],
        "inverse_blocker_penalty_score": 1.0 - hit["blocker_penalty_score"],
        "cross_family_flag": float(hit["is_cross_family"]),
        "holdout_flag": 1.0 if hit["candidate_evaluation_split"] == "holdout" else 0.0,
        "base_reranker_score": hit["reranker_score"],
    }


def train_mode_models(training_rows):
    by_mode = defaultdict(list)
    for row in training_rows:
        by_mode[row["mining_mode"]].append(row)

    models = {}
    for mining_mode, mode_rows in by_mode.items():
        positives = [row for row in mode_rows if row["label"] == 1]
        negatives = [row for row in mode_rows if row["label"] == 0]
        feature_names = list(feature_vector(mode_rows[0]).keys())
        if not positives or not negatives:
            models[mining_mode] = {
                "kind": "heuristic_only",
                "feature_names": feature_names,
                "weights": {},
                "means": {},
                "stds": {},
                "positive_count": len(positives),
                "negative_count": len(negatives),
                "training_example_count": len(mode_rows),
            }
            continue
        means = {}
        stds = {}
        for feature_name in feature_names:
            values = [feature_vector(row)[feature_name] for row in mode_rows]
            mean_value = sum(values) / len(values)
            variance = sum((value - mean_value) ** 2 for value in values) / len(values)
            means[feature_name] = mean_value
            stds[feature_name] = math.sqrt(variance) or 1.0
        weights = {}
        for feature_name in feature_names:
            positive_mean = sum(
                (feature_vector(row)[feature_name] - means[feature_name]) / stds[feature_name]
                for row in positives
            ) / len(positives)
            negative_mean = sum(
                (feature_vector(row)[feature_name] - means[feature_name]) / stds[feature_name]
                for row in negatives
            ) / len(negatives)
            weights[feature_name] = positive_mean - negative_mean
        models[mining_mode] = {
            "kind": "bootstrap_linear",
            "feature_names": feature_names,
            "weights": weights,
            "means": means,
            "stds": stds,
            "intercept": math.log((len(positives) + 1.0) / (len(negatives) + 1.0)),
            "positive_count": len(positives),
            "negative_count": len(negatives),
            "training_example_count": len(mode_rows),
        }
    return models


def model_score(hit, model):
    base_score = hit["reranker_score"]
    if model is None or model["kind"] != "bootstrap_linear":
        return clamp(base_score), "heuristic_only"
    linear_score = model["intercept"]
    vector = feature_vector(hit)
    for feature_name in model["feature_names"]:
        z_score = (vector[feature_name] - model["means"][feature_name]) / model["stds"][feature_name]
        linear_score += model["weights"][feature_name] * z_score
    learned_score = sigmoid(linear_score)
    return clamp(0.55 * learned_score + 0.45 * base_score), "bootstrap_linear"


def persist_weight_updates(
    connection,
    run_id: str,
    queryless_run_id: str,
    exposure_run_id: str | None,
    mining_version: str,
    score_version: str,
    models,
):
    update_ids = {}
    for mining_mode, model in models.items():
        metrics_payload = {
            "model_kind": model["kind"],
            "training_example_count": model["training_example_count"],
            "positive_example_count": model["positive_count"],
            "negative_example_count": model["negative_count"],
        }
        cursor = connection.execute(
            """
            INSERT INTO analyst_weight_updates (
              run_id,
              queryless_run_id,
              exposure_run_id,
              mining_version,
              score_version,
              mining_mode,
              update_kind,
              target_label_kind,
              training_example_count,
              positive_example_count,
              negative_example_count,
              weights_json,
              metrics_json,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, mining_mode, update_kind, target_label_kind) DO UPDATE SET
              exposure_run_id = excluded.exposure_run_id,
              training_example_count = excluded.training_example_count,
              positive_example_count = excluded.positive_example_count,
              negative_example_count = excluded.negative_example_count,
              weights_json = excluded.weights_json,
              metrics_json = excluded.metrics_json,
              updated_at = excluded.updated_at
            RETURNING analyst_weight_update_id
            """,
            (
                run_id,
                queryless_run_id,
                exposure_run_id,
                mining_version,
                score_version,
                mining_mode,
                "mode_reranker",
                "accept",
                model["training_example_count"],
                model["positive_count"],
                model["negative_count"],
                json.dumps(
                    {
                        "feature_names": model["feature_names"],
                        "weights": model.get("weights", {}),
                        "means": model.get("means", {}),
                        "stds": model.get("stds", {}),
                    },
                    sort_keys=True,
                ),
                json.dumps(metrics_payload, sort_keys=True),
                now_utc(),
            ),
        )
        update_ids[mining_mode] = cursor.fetchone()[0]
    return update_ids


def rerank_hits(hits, models):
    reranked_rows = []
    grouped = defaultdict(list)
    for hit in hits.values():
        adjusted_score, model_kind = model_score(hit, models.get(hit["mining_mode"]))
        grouped[(hit["source_mechanism_instance_id"], hit["mining_mode"])].append(
            {
                **hit,
                "adjusted_score": adjusted_score,
                "model_kind": model_kind,
                "score_delta": adjusted_score - hit["reranker_score"],
            }
        )
    for (_, mining_mode), group_rows in grouped.items():
        ranked_rows = sorted(
            group_rows,
            key=lambda row: (
                -row["adjusted_score"],
                -row["transfer_plausibility_score"],
                row["candidate_mechanism_instance_id"],
            ),
        )
        for rank, row in enumerate(ranked_rows, start=1):
            reranked_rows.append(
                {
                    **row,
                    "adjusted_rank_within_source": rank,
                    "mining_mode": mining_mode,
                }
            )
    return reranked_rows


def persist_reranked_hits(connection, reranked_rows, run_id: str, update_ids):
    for row in reranked_rows:
        support_payload = {
            "model_kind": row["model_kind"],
            "original_reranker_score": row["reranker_score"],
            "structural_similarity_score": row["structural_similarity_score"],
            "lexical_distance_score": row["lexical_distance_score"],
            "transfer_plausibility_score": row["transfer_plausibility_score"],
            "blocker_penalty_score": row["blocker_penalty_score"],
        }
        connection.execute(
            """
            INSERT INTO adjudicated_queryless_hits (
              queryless_candidate_hit_id,
              run_id,
              analyst_weight_update_id,
              queryless_run_id,
              mining_mode,
              source_mechanism_instance_id,
              candidate_mechanism_instance_id,
              adjusted_score,
              adjusted_rank_within_source,
              score_delta,
              support_json,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(queryless_candidate_hit_id, run_id) DO UPDATE SET
              analyst_weight_update_id = excluded.analyst_weight_update_id,
              queryless_run_id = excluded.queryless_run_id,
              mining_mode = excluded.mining_mode,
              adjusted_score = excluded.adjusted_score,
              adjusted_rank_within_source = excluded.adjusted_rank_within_source,
              score_delta = excluded.score_delta,
              support_json = excluded.support_json,
              updated_at = excluded.updated_at
            """,
            (
                row["queryless_candidate_hit_id"],
                run_id,
                update_ids.get(row["mining_mode"]),
                row["queryless_run_id"],
                row["mining_mode"],
                row["source_mechanism_instance_id"],
                row["candidate_mechanism_instance_id"],
                row["adjusted_score"],
                row["adjusted_rank_within_source"],
                row["score_delta"],
                json.dumps(support_payload, sort_keys=True),
                now_utc(),
            ),
        )


def rerun_exposure_scoring(connection, score_version: str, exposure_run_id: str):
    scoring_args = SimpleNamespace(paper_id=[], mechanism_instance_id=[], limit=None)
    rows = exposure_scoring.load_mechanisms(connection, scoring_args)
    label_counts = exposure_scoring.load_label_counts(connection)
    feature_rows = exposure_scoring.build_feature_rows(rows, label_counts)
    training_rows = exposure_scoring.derive_training_rows(feature_rows)
    model = exposure_scoring.train_bootstrap_model(training_rows)
    scored_count = exposure_scoring.persist_scores(
        connection, feature_rows, exposure_run_id, score_version, model
    )
    return {
        "scored_count": scored_count,
        "model_kind": model["kind"],
        "positive_training_rows": model["positive_count"],
        "negative_training_rows": model["negative_count"],
    }


def summarize(run_id, queryless_run_id, exposure_run_id, inserted_labels, labeled_hit_ids, models, reranked_rows, exposure_summary):
    by_mode = defaultdict(list)
    for row in reranked_rows:
        by_mode[row["mining_mode"]].append(row)
    return {
        "run_id": run_id,
        "queryless_run_id": queryless_run_id,
        "exposure_run_id": exposure_run_id,
        "inserted_label_count": inserted_labels,
        "labeled_hit_count": len(labeled_hit_ids),
        "mode_summary": {
            mining_mode: {
                "training_example_count": models[mining_mode]["training_example_count"],
                "positive_example_count": models[mining_mode]["positive_count"],
                "negative_example_count": models[mining_mode]["negative_count"],
                "top_adjusted_score": max(row["adjusted_score"] for row in mode_rows),
            }
            for mining_mode, mode_rows in by_mode.items()
        },
        "exposure_refresh": exposure_summary,
    }


def write_summary(run_id: str, summary):
    run_dir = ROOT / "data" / "structural-analogy" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "analyst_adjudication_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary_path


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    schema_sql_path = Path(args.schema_sql_path).resolve()
    labels_path = Path(args.labels_path).resolve()

    connection = sqlite3.connect(str(db_path))
    try:
        ensure_store_contract(connection, schema_sql_path)
        run_id = ensure_run(connection, args.run_id, args)
        exposure_run_id = None
        if not args.skip_exposure_refresh:
            exposure_run_id = f"{run_id}-exposure-refresh"
            exposure_scoring.ensure_run(connection, exposure_run_id, args.score_version)
        connection.commit()

        label_records = parse_json_lines(labels_path)
        hits_by_id, hits_by_signature = load_queryless_hits(
            connection, args.queryless_run_id, args.mining_version
        )
        if not hits_by_id:
            raise SystemExit(
                "queryless_candidate_hits are missing for the requested run; complete C11 mining first"
            )
        label_rows, labeled_hit_ids = build_label_rows(
            label_records, hits_by_id, hits_by_signature, args.created_by
        )
        if not label_rows:
            raise SystemExit("no analyst labels were materialized from the supplied JSONL")

        connection.execute("BEGIN")
        try:
            inserted_labels = persist_labels(connection, label_rows)
            hits, training_rows = load_adjudicated_hits(connection)
            if not training_rows:
                raise SystemExit("analyst labels did not yield any trainable adjudication rows")
            models = train_mode_models(training_rows)
            exposure_summary = None
            if exposure_run_id is not None:
                exposure_summary = rerun_exposure_scoring(
                    connection, args.score_version, exposure_run_id
                )
            update_ids = persist_weight_updates(
                connection,
                run_id,
                args.queryless_run_id,
                exposure_run_id,
                args.mining_version,
                args.score_version,
                models,
            )
            reranked_rows = rerank_hits(hits, models)
            persist_reranked_hits(connection, reranked_rows, run_id, update_ids)
            connection.execute(
                """
                UPDATE extraction_runs
                SET run_status = ?, completed_at = ?
                WHERE run_id IN (?, COALESCE(?, ?))
                """,
                ("completed", now_utc(), run_id, exposure_run_id, run_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()

    summary = summarize(
        run_id,
        args.queryless_run_id,
        exposure_run_id,
        inserted_labels,
        labeled_hit_ids,
        models,
        reranked_rows,
        exposure_summary,
    )
    summary_path = write_summary(run_id, summary)
    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
