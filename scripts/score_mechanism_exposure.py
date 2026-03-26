#!/usr/bin/env python3

import argparse
import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_SCHEMA_SQL_PATH = ROOT / "sql" / "paperview_schema.sql"
DEFAULT_SCORE_VERSION = "c09-exposure-v1"
DEFAULT_RUN_KIND = "exposure_scoring"
DEFAULT_MODEL_NAME = "c09-bootstrap-linear-v1"

EVIDENCE_STRENGTH_SCORE = {
    "strong": 1.0,
    "moderate": 0.7,
    "medium": 0.7,
    "weak": 0.35,
    "unscored": 0.25,
}
TRADECORE_FIT_SCORE = {"high": 1.0, "medium": 0.6, "low": 0.2}
LIKELY_CROWDING_SCORE = {"high": 1.0, "medium": 0.6, "low": 0.2, "other": 0.35}
POSITIVE_ANALYST_KINDS = {
    "accept",
    "worth_strategy_follow_up",
    "worth_strategy_brief",
    "genuinely_new",
    "structurally_relevant",
    "non_obvious",
}
POSITIVE_LABEL_VALUES = {"accept", "accepted", "yes", "true", "1", "high", "worth_it"}
NEGATIVE_LABEL_VALUES = {"reject", "rejected", "no", "false", "0", "low", "not_worth_it"}
POSITIVE_PAIR_KINDS = {"true_far_analog", "obvious_neighbor"}
NEGATIVE_PAIR_KINDS = {"hard_negative"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute mechanism-level exposure and underexploited scores."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--schema-sql-path",
        default=str(DEFAULT_SCHEMA_SQL_PATH),
        help="Path to the SQL schema to apply before scoring.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit scoring run id.",
    )
    parser.add_argument(
        "--score-version",
        default=DEFAULT_SCORE_VERSION,
        help="Score contract version to persist.",
    )
    parser.add_argument(
        "--paper-id",
        action="append",
        default=[],
        help="Restrict scoring to one or more paper ids.",
    )
    parser.add_argument(
        "--mechanism-instance-id",
        action="append",
        type=int,
        default=[],
        help="Restrict scoring to one or more mechanism instance ids.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of mechanism instances to score.",
    )
    return parser.parse_args()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def sigmoid(value: float) -> float:
    if value >= 0:
        exp_value = math.exp(-value)
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def parse_json_array(value):
    if not value:
        return []
    decoded = json.loads(value)
    return decoded if isinstance(decoded, list) else []


def parse_json_object(value):
    if not value:
        return {}
    decoded = json.loads(value)
    return decoded if isinstance(decoded, dict) else {}


def avg(values):
    materialized = list(values)
    return sum(materialized) / len(materialized) if materialized else 0.0


def ensure_store_contract(connection, schema_sql_path: Path):
    connection.executescript(schema_sql_path.read_text(encoding="utf-8"))


def ensure_run(connection, run_id: str | None, score_version: str):
    resolved_run_id = run_id or (
        f"{DEFAULT_RUN_KIND}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    config = {
        "score_version": score_version,
        "run_kind": DEFAULT_RUN_KIND,
        "model_name": DEFAULT_MODEL_NAME,
    }
    existing = connection.execute(
        """
        SELECT run_id
        FROM extraction_runs
        WHERE run_id = ?
        """,
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
                DEFAULT_MODEL_NAME,
                score_version,
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
                DEFAULT_MODEL_NAME,
                score_version,
                json.dumps(config, sort_keys=True),
                "running",
                resolved_run_id,
            ),
        )
    return resolved_run_id


def build_filters(args):
    clauses = ["mi.lifecycle_status = 'active'"]
    params = []
    if args.paper_id:
        placeholders = ", ".join("?" for _ in args.paper_id)
        clauses.append(f"mi.paper_id IN ({placeholders})")
        params.extend(args.paper_id)
    if args.mechanism_instance_id:
        placeholders = ", ".join("?" for _ in args.mechanism_instance_id)
        clauses.append(f"mi.mechanism_instance_id IN ({placeholders})")
        params.extend(args.mechanism_instance_id)
    limit_clause = f" LIMIT {args.limit}" if args.limit is not None else ""
    return " AND ".join(clauses), params, limit_clause


def load_mechanisms(connection, args):
    connection.row_factory = sqlite3.Row
    where_clause, params, limit_clause = build_filters(args)
    query = f"""
        SELECT
          mi.mechanism_instance_id,
          mi.paper_id,
          mi.mechanism_label,
          mi.mechanism_summary,
          mi.evidence_confidence,
          mi.insight_type,
          mi.required_assumptions_json,
          mi.fragility_flags_json,
          mi.capacity_constraints_json,
          mi.mechanism_json,
          p.literature_family,
          p.evaluation_split,
          mf.fingerprint_text,
          mf.trigger_json,
          mf.market_topology_json,
          mf.portability_blockers_json,
          mf.ambiguity_flags_json
        FROM mechanism_instances mi
        JOIN papers p
          ON p.paper_id = mi.paper_id
        JOIN mechanism_fingerprints mf
          ON mf.mechanism_instance_id = mi.mechanism_instance_id
         AND mf.mechanism_fingerprint_id = (
           SELECT mf2.mechanism_fingerprint_id
           FROM mechanism_fingerprints mf2
           WHERE mf2.mechanism_instance_id = mi.mechanism_instance_id
           ORDER BY mf2.updated_at DESC, mf2.mechanism_fingerprint_id DESC
           LIMIT 1
         )
        WHERE {where_clause}
        ORDER BY mi.mechanism_instance_id
        {limit_clause}
    """
    return connection.execute(query, params).fetchall()


def load_label_counts(connection):
    label_counts = defaultdict(lambda: {"positive": 0, "negative": 0})
    for mechanism_instance_id, label_kind, label_value in connection.execute(
        """
        SELECT mechanism_instance_id, label_kind, label_value
        FROM analyst_labels
        WHERE mechanism_instance_id IS NOT NULL
        """
    ):
        normalized_kind = (label_kind or "").strip().lower()
        normalized_value = (label_value or "").strip().lower()
        if normalized_kind not in POSITIVE_ANALYST_KINDS:
            continue
        if normalized_value in POSITIVE_LABEL_VALUES:
            label_counts[mechanism_instance_id]["positive"] += 1
        elif normalized_value in NEGATIVE_LABEL_VALUES:
            label_counts[mechanism_instance_id]["negative"] += 1

    # @context decision -- C09 only bootstraps benchmark supervision from
    # benchmark pairs that already resolve to canonical mechanism ids. The
    # paper-level bridge from C04 stays useful, but scoring must not invent
    # mechanism labels for multi-mechanism papers while C12 feedback is absent.
    for source_id, candidate_id, pair_kind in connection.execute(
        """
        SELECT source_mechanism_instance_id, candidate_mechanism_instance_id, pair_kind
        FROM benchmark_pairs
        WHERE source_mechanism_instance_id IS NOT NULL
           OR candidate_mechanism_instance_id IS NOT NULL
        """
    ):
        if pair_kind in POSITIVE_PAIR_KINDS:
            delta_key = "positive"
        elif pair_kind in NEGATIVE_PAIR_KINDS:
            delta_key = "negative"
        else:
            continue
        for mechanism_instance_id in (source_id, candidate_id):
            if mechanism_instance_id is None:
                continue
            label_counts[mechanism_instance_id][delta_key] += 1
    return label_counts


def build_feature_rows(rows, label_counts):
    total_rows = len(rows)
    family_counts = Counter(row["literature_family"] for row in rows)
    fingerprint_counts = Counter(row["fingerprint_text"] for row in rows)
    trigger_counts = Counter()
    topology_counts = Counter()
    for row in rows:
        for label in parse_json_array(row["trigger_json"]):
            trigger_counts[label] += 1
        for label in parse_json_array(row["market_topology_json"]):
            topology_counts[label] += 1

    feature_rows = []
    for row in rows:
        mechanism_json = parse_json_object(row["mechanism_json"])
        triggers = parse_json_array(row["trigger_json"])
        topology = parse_json_array(row["market_topology_json"])
        portability_blockers = parse_json_array(row["portability_blockers_json"])
        ambiguity_flags = parse_json_array(row["ambiguity_flags_json"])
        family_share = family_counts[row["literature_family"]] / total_rows
        trigger_share = avg(trigger_counts[label] / total_rows for label in triggers) if triggers else 0.0
        topology_share = avg(topology_counts[label] / total_rows for label in topology) if topology else 0.0
        duplicate_share = fingerprint_counts[row["fingerprint_text"]] / total_rows
        benchmark_counts = label_counts.get(
            row["mechanism_instance_id"], {"positive": 0, "negative": 0}
        )
        positive_count = benchmark_counts["positive"]
        negative_count = benchmark_counts["negative"]
        benchmark_support = (
            positive_count / (positive_count + negative_count)
            if positive_count + negative_count > 0
            else 0.0
        )
        evidence_strength_score = EVIDENCE_STRENGTH_SCORE.get(
            row["evidence_confidence"], 0.25
        )
        tradecore_fit_score = TRADECORE_FIT_SCORE.get(
            mechanism_json.get("tradecore_fit", "low"), 0.2
        )
        crowding_score = LIKELY_CROWDING_SCORE.get(
            mechanism_json.get("likely_crowding", "other"), 0.35
        )
        ambiguity_burden = clamp(len(ambiguity_flags) / 4.0)
        portability_burden = clamp(len(portability_blockers) / 4.0)
        family_frontier_score = 1.0 if row["literature_family"] != "q_fin" else 0.35
        holdout_flag = 1.0 if row["evaluation_split"] == "holdout" else 0.0
        exposure_score = clamp(
            0.25 * family_share
            + 0.15 * trigger_share
            + 0.15 * topology_share
            + 0.25 * duplicate_share
            + 0.20 * crowding_score
        )
        # @context requirement -- C09 treats "underexploited" as fit under
        # plausible transfer constraints, not as raw novelty. High-fit rows with
        # heavy portability blockers or normalization ambiguity must score down
        # even when the mechanism is lexically uncommon.
        underexploited_score = clamp(
            0.28 * tradecore_fit_score
            + 0.15 * evidence_strength_score
            + 0.17 * (1.0 - exposure_score)
            + 0.10 * benchmark_support
            + 0.08 * family_frontier_score
            + 0.07 * holdout_flag
            + 0.10 * (1.0 - portability_burden)
            + 0.05 * (1.0 - crowding_score)
            - 0.10 * ambiguity_burden
        )
        feature_vector = {
            "tradecore_fit_score": tradecore_fit_score,
            "evidence_strength_score": evidence_strength_score,
            "novelty_score": 1.0 - exposure_score,
            "frontier_family_score": family_frontier_score,
            "holdout_flag": holdout_flag,
            "benchmark_support": benchmark_support,
            "inverse_portability_burden": 1.0 - portability_burden,
            "inverse_ambiguity_burden": 1.0 - ambiguity_burden,
            "inverse_crowding_score": 1.0 - crowding_score,
        }
        feature_rows.append(
            {
                "mechanism_instance_id": row["mechanism_instance_id"],
                "paper_id": row["paper_id"],
                "literature_family": row["literature_family"],
                "evaluation_split": row["evaluation_split"],
                "exposure_score": exposure_score,
                "underexploited_score": underexploited_score,
                "family_share": family_share,
                "trigger_share": trigger_share,
                "topology_share": topology_share,
                "duplicate_share": duplicate_share,
                "benchmark_support": benchmark_support,
                "ambiguity_burden": ambiguity_burden,
                "portability_burden": portability_burden,
                "evidence_strength_score": evidence_strength_score,
                "tradecore_fit_score": tradecore_fit_score,
                "crowding_score": crowding_score,
                "positive_label_count": positive_count,
                "negative_label_count": negative_count,
                "feature_vector": feature_vector,
            }
        )
    return feature_rows


def derive_training_rows(feature_rows):
    labeled_rows = []
    for row in feature_rows:
        if row["positive_label_count"] == row["negative_label_count"]:
            continue
        labeled_rows.append(
            {
                "label": 1 if row["positive_label_count"] > row["negative_label_count"] else 0,
                "feature_vector": row["feature_vector"],
            }
        )
    return labeled_rows


def train_bootstrap_model(labeled_rows):
    feature_names = list(labeled_rows[0]["feature_vector"].keys())
    means = {}
    stds = {}
    for feature_name in feature_names:
        values = [row["feature_vector"][feature_name] for row in labeled_rows]
        mean_value = sum(values) / len(values)
        variance = sum((value - mean_value) ** 2 for value in values) / len(values)
        means[feature_name] = mean_value
        stds[feature_name] = math.sqrt(variance) or 1.0

    positives = [row for row in labeled_rows if row["label"] == 1]
    negatives = [row for row in labeled_rows if row["label"] == 0]
    if not positives or not negatives:
        return {
            "kind": "heuristic_only",
            "feature_names": feature_names,
            "means": means,
            "stds": stds,
            "weights": {},
            "intercept": 0.0,
            "positive_count": len(positives),
            "negative_count": len(negatives),
        }

    weights = {}
    for feature_name in feature_names:
        positive_mean = avg(
            (
                (row["feature_vector"][feature_name] - means[feature_name]) / stds[feature_name]
                for row in positives
            )
        )
        negative_mean = avg(
            (
                (row["feature_vector"][feature_name] - means[feature_name]) / stds[feature_name]
                for row in negatives
            )
        )
        weights[feature_name] = positive_mean - negative_mean

    return {
        "kind": "bootstrap_linear",
        "feature_names": feature_names,
        "means": means,
        "stds": stds,
        "weights": weights,
        "intercept": math.log((len(positives) + 1.0) / (len(negatives) + 1.0)),
        "positive_count": len(positives),
        "negative_count": len(negatives),
    }


def score_followup_prior(feature_row, model):
    heuristic_prior = clamp(
        0.45 * feature_row["underexploited_score"]
        + 0.20 * feature_row["benchmark_support"]
        + 0.20 * feature_row["tradecore_fit_score"]
        + 0.10 * (1.0 - feature_row["ambiguity_burden"])
        + 0.05 * (1.0 - feature_row["crowding_score"])
    )
    if model["kind"] != "bootstrap_linear":
        return heuristic_prior, "heuristic_only"

    linear_score = model["intercept"]
    for feature_name in model["feature_names"]:
        raw_value = feature_row["feature_vector"][feature_name]
        z_score = (raw_value - model["means"][feature_name]) / model["stds"][feature_name]
        linear_score += model["weights"][feature_name] * z_score
    learned_prior = sigmoid(linear_score)
    return clamp(0.6 * learned_prior + 0.4 * heuristic_prior), "bootstrap_linear"


def persist_scores(connection, feature_rows, run_id: str, score_version: str, model):
    scored_count = 0
    for row in feature_rows:
        worth_followup_score, model_kind = score_followup_prior(row, model)
        feature_payload = {
            "feature_vector": row["feature_vector"],
            "positive_label_count": row["positive_label_count"],
            "negative_label_count": row["negative_label_count"],
        }
        model_payload = {
            "model_name": DEFAULT_MODEL_NAME,
            "model_kind": model_kind,
            "score_version": score_version,
            "positive_count": model["positive_count"],
            "negative_count": model["negative_count"],
        }
        connection.execute(
            """
            INSERT INTO mechanism_exposure_scores (
              mechanism_instance_id,
              paper_id,
              run_id,
              score_version,
              literature_family,
              evaluation_split,
              exposure_score,
              underexploited_score,
              worth_followup_score,
              family_share,
              trigger_share,
              topology_share,
              duplicate_share,
              benchmark_support,
              ambiguity_burden,
              portability_burden,
              evidence_strength_score,
              tradecore_fit_score,
              crowding_score,
              feature_json,
              model_json,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mechanism_instance_id, run_id, score_version) DO UPDATE SET
              paper_id = excluded.paper_id,
              literature_family = excluded.literature_family,
              evaluation_split = excluded.evaluation_split,
              exposure_score = excluded.exposure_score,
              underexploited_score = excluded.underexploited_score,
              worth_followup_score = excluded.worth_followup_score,
              family_share = excluded.family_share,
              trigger_share = excluded.trigger_share,
              topology_share = excluded.topology_share,
              duplicate_share = excluded.duplicate_share,
              benchmark_support = excluded.benchmark_support,
              ambiguity_burden = excluded.ambiguity_burden,
              portability_burden = excluded.portability_burden,
              evidence_strength_score = excluded.evidence_strength_score,
              tradecore_fit_score = excluded.tradecore_fit_score,
              crowding_score = excluded.crowding_score,
              feature_json = excluded.feature_json,
              model_json = excluded.model_json,
              updated_at = excluded.updated_at
            """,
            (
                row["mechanism_instance_id"],
                row["paper_id"],
                run_id,
                score_version,
                row["literature_family"],
                row["evaluation_split"],
                row["exposure_score"],
                row["underexploited_score"],
                worth_followup_score,
                row["family_share"],
                row["trigger_share"],
                row["topology_share"],
                row["duplicate_share"],
                row["benchmark_support"],
                row["ambiguity_burden"],
                row["portability_burden"],
                row["evidence_strength_score"],
                row["tradecore_fit_score"],
                row["crowding_score"],
                json.dumps(feature_payload, sort_keys=True),
                json.dumps(model_payload, sort_keys=True),
                now_utc(),
            ),
        )
        scored_count += 1
    return scored_count


def summarize(feature_rows, run_id: str, score_version: str, model):
    families = Counter(row["literature_family"] for row in feature_rows)
    return {
        "run_id": run_id,
        "score_version": score_version,
        "scored_count": len(feature_rows),
        "literature_family_counts": dict(sorted(families.items())),
        "avg_exposure_score": round(avg(row["exposure_score"] for row in feature_rows), 6)
        if feature_rows
        else 0.0,
        "avg_underexploited_score": round(
            avg(row["underexploited_score"] for row in feature_rows), 6
        )
        if feature_rows
        else 0.0,
        "model_kind": model["kind"],
        "positive_training_rows": model["positive_count"],
        "negative_training_rows": model["negative_count"],
    }


def write_summary(run_id: str, summary):
    run_dir = ROOT / "data" / "structural-analogy" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "exposure_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary_path


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    schema_sql_path = Path(args.schema_sql_path).resolve()

    connection = sqlite3.connect(str(db_path))
    try:
        ensure_store_contract(connection, schema_sql_path)
        run_id = ensure_run(connection, args.run_id, args.score_version)
        connection.commit()
        rows = load_mechanisms(connection, args)
        if not rows:
            raise SystemExit(
                "no active mechanism instances with fingerprints found; run C05/C08 data prep first"
            )

        label_counts = load_label_counts(connection)
        feature_rows = build_feature_rows(rows, label_counts)
        training_rows = derive_training_rows(feature_rows)
        if len(training_rows) >= 4:
            model = train_bootstrap_model(training_rows)
        else:
            feature_names = list(feature_rows[0]["feature_vector"].keys())
            model = {
                "kind": "heuristic_only",
                "feature_names": feature_names,
                "means": {name: 0.0 for name in feature_names},
                "stds": {name: 1.0 for name in feature_names},
                "weights": {},
                "intercept": 0.0,
                "positive_count": sum(1 for row in training_rows if row["label"] == 1),
                "negative_count": sum(1 for row in training_rows if row["label"] == 0),
            }

        connection.execute("BEGIN")
        try:
            scored_count = persist_scores(connection, feature_rows, run_id, args.score_version, model)
            connection.execute(
                """
                UPDATE extraction_runs
                SET run_status = ?, completed_at = ?
                WHERE run_id = ?
                """,
                ("completed", now_utc(), run_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    finally:
        connection.close()

    summary = summarize(feature_rows, run_id, args.score_version, model)
    summary["persisted_count"] = scored_count
    summary_path = write_summary(run_id, summary)
    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
