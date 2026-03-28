#!/usr/bin/env python3

import argparse
import json
import math
import re
import sqlite3
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_SIGNAL_CONFIG_PATH = ROOT / "configs" / "stranding_signals.yaml"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize canonical sparse stranding scores.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="stranding-score-materialization-20260328")
    parser.add_argument("--membership-run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--signal-config-path", default=str(DEFAULT_SIGNAL_CONFIG_PATH))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--top-k", type=int, default=50)
    return parser.parse_args()


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def is_negated(prefix: str, negation_terms: list[str]) -> bool:
    lowered = prefix.lower()
    return any(re.search(r"\b" + re.escape(str(term).lower()) + r"\b", lowered) for term in negation_terms)


def keyword_hits(
    text: str,
    phrase_entries: list[dict],
    negation_terms: list[str],
    negation_window_chars: int,
) -> list[dict]:
    lowered = (text or "").lower()
    hits = []
    for entry in phrase_entries:
        phrase = entry["phrase"]
        pattern = r"\b" + re.escape(phrase.lower()) + r"\b"
        for match in re.finditer(pattern, lowered):
            # @context risk -- Sparse stranding cues are meant to capture asserted constraints, not
            # phrases denied by the paper. Without a local negation guard, strings like "not
            # illiquid" or "without settlement delay" inflate the stranded-result prior.
            prefix = lowered[max(0, match.start() - negation_window_chars) : match.start()]
            if is_negated(prefix, negation_terms):
                continue
            hits.append(entry)
            break
    return hits


def normalized_score(weight_total: float, cap: float, saturation_mode: str) -> float:
    if weight_total <= 0:
        return 0.0
    ratio = weight_total / cap
    if saturation_mode == "exponential":
        return 1.0 - math.exp(-ratio)
    return min(1.0, ratio)


def normalize_phrase_entries(raw_entries: list[object]) -> list[dict]:
    normalized = []
    for raw in raw_entries:
        if isinstance(raw, dict):
            normalized.append({"phrase": str(raw["phrase"]), "weight": float(raw.get("weight", 1.0))})
        else:
            normalized.append({"phrase": str(raw), "weight": 1.0})
    return normalized


def fetch_membership_sets(connection: sqlite3.Connection, membership_run_id: str) -> tuple[set[str], set[str]]:
    rows = connection.execute(
        """
        SELECT paper_id, corpus_id
        FROM corpus_memberships
        WHERE run_id = ?
        """,
        (membership_run_id,),
    ).fetchall()
    if not rows:
        raise SystemExit(f"no corpus memberships found for run_id={membership_run_id}")
    discovery = {row["paper_id"] for row in rows if row["corpus_id"] == "discovery"}
    stranded_alpha = {row["paper_id"] for row in rows if row["corpus_id"] == "stranded_alpha"}
    return discovery, stranded_alpha


def build_score_rows(connection: sqlite3.Connection, membership_run_id: str, signal_config: dict) -> list[dict]:
    discovery_ids, stranded_alpha_ids = fetch_membership_sets(connection, membership_run_id)
    rows = connection.execute(
        """
        SELECT paper_id, title, abstract, primary_category, published_at
        FROM papers
        ORDER BY paper_id
        """
    ).fetchall()
    weights = signal_config["weights"]
    signal_sets = {
        feature_name: normalize_phrase_entries(raw_entries)
        for feature_name, raw_entries in signal_config["signals"].items()
    }
    signal_caps = {feature_name: float(cap) for feature_name, cap in signal_config["signal_caps"].items()}
    saturation_mode = str(signal_config.get("saturation_mode", "linear"))
    negation_terms = signal_config.get("negation_terms", [])
    negation_window_chars = int(signal_config.get("negation_window_chars", 48))
    scored_rows = []
    for row in rows:
        paper_id = row["paper_id"]
        if paper_id not in discovery_ids:
            continue
        text = f"{row['title'] or ''}\n{row['abstract'] or ''}"
        feature_hits = {
            feature_name: keyword_hits(text, phrases, negation_terms, negation_window_chars)
            for feature_name, phrases in signal_sets.items()
        }
        signal_weight_totals = {
            feature_name: sum(hit["weight"] for hit in hits)
            for feature_name, hits in feature_hits.items()
        }
        instrument_gap_score = normalized_score(
            signal_weight_totals["instrument_gap"], signal_caps["instrument_gap"], saturation_mode
        )
        access_barrier_score = normalized_score(
            signal_weight_totals["access_barrier"], signal_caps["access_barrier"], saturation_mode
        )
        result_specificity_score = normalized_score(
            signal_weight_totals["result_specificity"], signal_caps["result_specificity"], saturation_mode
        )
        resolution_mechanics_score = normalized_score(
            signal_weight_totals["resolution_mechanics"], signal_caps["resolution_mechanics"], saturation_mode
        )
        positive_family_count = sum(
            1
            for feature_name in (
                "instrument_gap",
                "access_barrier",
                "result_specificity",
                "resolution_mechanics",
            )
            if signal_weight_totals[feature_name] > 0
        )
        low_diversity_penalty_score = 1.0 if positive_family_count < 2 else 0.0
        survey_penalty_score = normalized_score(
            signal_weight_totals["survey_penalty"], signal_caps["survey_penalty"], saturation_mode
        )
        empirical_only_penalty_score = normalized_score(
            signal_weight_totals["empirical_only_penalty"], signal_caps["empirical_only_penalty"], saturation_mode
        )
        stranded_alpha_bonus = 1.0 if paper_id in stranded_alpha_ids else 0.0

        # @context decision -- The first S08 surface is intentionally sparse and auditable: it uses
        # weighted phrase families plus a stranded-alpha bonus, not an opaque learned model. Strong
        # cues like `contingent claim` or `closed-form` should outrank weak generic wording such as
        # `characterize`, and later S08 commits can still refine this without breaking the contract.
        # @context requirement -- The stranding score must stay continuous for the final composite
        # ranking, but weak one-family matches cannot dominate the surface. Penalizing low-diversity
        # positives preserves gradient behavior while demoting rows that only echo a single sparse cue.
        stranding_score = (
            weights["instrument_gap"] * instrument_gap_score
            + weights["access_barrier"] * access_barrier_score
            + weights["result_specificity"] * result_specificity_score
            + weights["resolution_mechanics"] * resolution_mechanics_score
            + weights["stranded_alpha_bonus"] * stranded_alpha_bonus
            - weights["low_diversity_penalty"] * low_diversity_penalty_score
            - weights["survey_penalty"] * survey_penalty_score
            - weights["empirical_only_penalty"] * empirical_only_penalty_score
        )
        stranding_score = max(0.0, min(1.0, stranding_score))

        feature_payload = {
            "hits": {
                feature_name: [hit["phrase"] for hit in hits] for feature_name, hits in feature_hits.items()
            },
            "weight_totals": signal_weight_totals,
            "saturation_mode": saturation_mode,
            "positive_family_count": positive_family_count,
            "low_diversity_penalty_score": low_diversity_penalty_score,
            "primary_category": row["primary_category"],
            "published_at": row["published_at"],
            "is_stranded_alpha": paper_id in stranded_alpha_ids,
        }
        scored_rows.append(
            {
                "paper_id": paper_id,
                "score_version": signal_config["score_version"],
                "stranding_score": round(stranding_score, 6),
                "instrument_gap_score": instrument_gap_score,
                "access_barrier_score": access_barrier_score,
                "result_specificity_score": result_specificity_score,
                "resolution_mechanics_score": resolution_mechanics_score,
                "survey_penalty_score": survey_penalty_score,
                "empirical_only_penalty_score": empirical_only_penalty_score,
                "stranded_alpha_bonus": stranded_alpha_bonus,
                "feature_json": json.dumps(feature_payload, sort_keys=True),
            }
        )
    return scored_rows


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    signal_config = load_yaml(Path(args.signal_config_path).resolve())

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        log_run_event(
            connection,
            args.run_id,
            "stranding_scores",
            "started",
            {
                "membership_run_id": args.membership_run_id,
                "signal_config_path": str(Path(args.signal_config_path).resolve()),
            },
        )
        rows = build_score_rows(connection, args.membership_run_id, signal_config)
        connection.execute("DELETE FROM stranding_scores WHERE run_id = ?", (args.run_id,))
        connection.executemany(
            """
            INSERT INTO stranding_scores (
              run_id,
              paper_id,
              membership_run_id,
              score_version,
              stranding_score,
              instrument_gap_score,
              access_barrier_score,
              result_specificity_score,
              resolution_mechanics_score,
              survey_penalty_score,
              empirical_only_penalty_score,
              stranded_alpha_bonus,
              feature_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    args.run_id,
                    row["paper_id"],
                    args.membership_run_id,
                    row["score_version"],
                    row["stranding_score"],
                    row["instrument_gap_score"],
                    row["access_barrier_score"],
                    row["result_specificity_score"],
                    row["resolution_mechanics_score"],
                    row["survey_penalty_score"],
                    row["empirical_only_penalty_score"],
                    row["stranded_alpha_bonus"],
                    row["feature_json"],
                )
                for row in rows
            ],
        )
        ranked_rows = sorted(rows, key=lambda row: (-row["stranding_score"], row["paper_id"]))
        top_preview = ranked_rows[: args.top_k]
        metrics = {
            "run_id": args.run_id,
            "membership_run_id": args.membership_run_id,
            "scored_papers": len(rows),
            "positive_score_papers": sum(1 for row in rows if row["stranding_score"] > 0),
            "stranded_alpha_positive_papers": sum(
                1 for row in rows if row["stranding_score"] > 0 and row["stranded_alpha_bonus"] > 0
            ),
            "top_score": top_preview[0]["stranding_score"] if top_preview else 0.0,
        }
        metrics_path = output_dir / "stranding_score_metrics.json"
        preview_path = output_dir / "stranding_score_top.jsonl"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        preview_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in top_preview),
            encoding="utf-8",
        )
        log_run_event(
            connection,
            args.run_id,
            "stranding_scores",
            "completed",
            {
                **metrics,
                "metrics_path": str(metrics_path),
                "preview_path": str(preview_path),
            },
        )
        connection.commit()
    finally:
        connection.close()

    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
