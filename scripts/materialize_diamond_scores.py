#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_CAPSULES_PATH = ROOT / "configs" / "challenge_capsules.yaml"
DEFAULT_REPORTS_DIR = ROOT / "reports"

LANES = (
    "transition_state",
    "market_design",
    "settlement_resolution",
    "participant_pathologies",
    "state_graph",
    "stranded_qfin",
)


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize canonical unified diamond scores and representations.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="diamond-score-materialization-20260329")
    parser.add_argument("--lane-score-run-id", default="lane-score-materialization-20260329")
    parser.add_argument("--membership-run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--challenge-capsules-path", default=str(DEFAULT_CAPSULES_PATH))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--top-k", type=int, default=100)
    return parser.parse_args()


def load_yaml(path: Path, default):
    if not path.exists() or yaml is None:
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def ensure_diamond_scores_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS diamond_scores (
          run_id TEXT NOT NULL,
          paper_id TEXT NOT NULL,
          lane_score_run_id TEXT NOT NULL,
          membership_run_id TEXT NOT NULL,
          score_version TEXT NOT NULL,
          diamond_score REAL NOT NULL,
          top_lane TEXT NOT NULL,
          top_lane_score REAL NOT NULL,
          primary_capsule_id TEXT,
          challenge_affinity_score REAL NOT NULL,
          positive_anchor_affinity_score REAL NOT NULL,
          negative_anchor_affinity_score REAL NOT NULL,
          translation_gap_score REAL NOT NULL,
          stranding_score REAL NOT NULL,
          bridge_score REAL NOT NULL,
          composition_score REAL NOT NULL,
          holdout_echo_score REAL NOT NULL,
          transition_state_score REAL NOT NULL,
          genericity_penalty_score REAL NOT NULL,
          realized_market_leakage_penalty_score REAL NOT NULL,
          lane_rarity_bonus REAL NOT NULL,
          positive_lane_count INTEGER NOT NULL,
          problem_view TEXT NOT NULL,
          mechanism_view TEXT NOT NULL,
          regime_view TEXT NOT NULL,
          stranding_view TEXT NOT NULL,
          feature_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, paper_id),
          FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_diamond_scores_run_rank
        ON diamond_scores(run_id, diamond_score DESC, paper_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_diamond_scores_run_lane
        ON diamond_scores(run_id, top_lane)
        """
    )


def normalize_text(text: str | None) -> str:
    return " ".join((text or "").split())


def normalize_translation_gap(value: float) -> float:
    return min(1.0, max(0.0, value) / 7.0)


def normalize_challenge_affinity(value: float) -> float:
    return min(1.0, max(0.0, value) / 2.0)


def normalize_positive_affinity(value: float) -> float:
    return min(1.0, max(0.0, value))


def normalize_negative_affinity(value: float) -> float:
    return min(1.0, max(0.0, value))


def normalize_realized_penalty(value: float) -> float:
    return min(1.0, max(0.0, value))


def normalize_holdout(verdict: str | None, score: float) -> float:
    score = max(0.0, float(score or 0.0))
    if verdict == "validation":
        return min(1.0, score)
    if verdict == "partial":
        return min(1.0, 0.6 * score)
    return 0.0


def load_capsule_defaults(payload: dict) -> dict[str, str]:
    by_lane = {}
    for capsule in payload.get("capsules", []):
        lane = capsule.get("lane")
        if lane in LANES and lane not in by_lane:
            by_lane[lane] = capsule["capsule_id"]
    return by_lane


def fetch_paper_metadata(connection: sqlite3.Connection) -> dict[str, dict]:
    rows = connection.execute(
        """
        SELECT paper_id, title, primary_category, published_at
        FROM papers
        ORDER BY paper_id
        """
    ).fetchall()
    return {
        row["paper_id"]: {
            "title": row["title"],
            "primary_category": row["primary_category"],
            "published_at": row["published_at"],
        }
        for row in rows
    }


def fetch_lane_rows(connection: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = connection.execute(
        """
        SELECT
          paper_id,
          transition_state_score,
          market_design_score,
          settlement_resolution_score,
          participant_pathologies_score,
          state_graph_score,
          stranded_qfin_score,
          lifecycle_aux_score,
          top_lane,
          top_lane_score,
          positive_lane_count,
          feature_json
        FROM diamond_lane_scores
        WHERE run_id = ?
        ORDER BY paper_id
        """,
        (run_id,),
    ).fetchall()
    return [
        {
            "paper_id": row["paper_id"],
            "transition_state_score": float(row["transition_state_score"] or 0.0),
            "market_design_score": float(row["market_design_score"] or 0.0),
            "settlement_resolution_score": float(row["settlement_resolution_score"] or 0.0),
            "participant_pathologies_score": float(row["participant_pathologies_score"] or 0.0),
            "state_graph_score": float(row["state_graph_score"] or 0.0),
            "stranded_qfin_score": float(row["stranded_qfin_score"] or 0.0),
            "lifecycle_aux_score": float(row["lifecycle_aux_score"] or 0.0),
            "top_lane": row["top_lane"],
            "top_lane_score": float(row["top_lane_score"] or 0.0),
            "positive_lane_count": int(row["positive_lane_count"] or 0),
            "feature_json": json.loads(row["feature_json"] or "{}"),
        }
        for row in rows
    ]


def max_component_score(feature_json: dict, source_name: str) -> float:
    best = 0.0
    for lane_components in feature_json.get("lane_components", {}).values():
        for ref in lane_components.get("evidence_refs", []):
            if ref.get("source") == source_name:
                best = max(best, float(ref.get("score") or 0.0))
    return best


def map_by_key(rows: list[dict], key: str) -> dict[str, dict]:
    return {row[key]: row for row in rows if key in row}


def choose_primary_capsule(lane_row: dict, ds1_row: dict | None, capsule_defaults: dict[str, str]) -> str | None:
    if ds1_row and ds1_row.get("challenge_capsule_matched"):
        return ds1_row["challenge_capsule_matched"]
    return capsule_defaults.get(lane_row["top_lane"])


def build_problem_view(ds4_row: dict | None, ds3_row: dict | None, ds1_row: dict | None, lane_row: dict) -> str:
    if ds4_row:
        return normalize_text(ds4_row.get("result_plain"))
    if ds3_row:
        return normalize_text(ds3_row.get("failure_mode"))
    if ds1_row:
        return normalize_text(ds1_row.get("why_far_from_realized"))
    return f"Paper ranks highest in the {lane_row['top_lane']} lane without a richer DS narrative yet."


def build_mechanism_view(
    ds4_row: dict | None,
    ds3_row: dict | None,
    ds1_row: dict | None,
    primary_capsule_id: str | None,
) -> str:
    if ds4_row:
        return normalize_text(ds4_row.get("modern_equivalent_now"))
    if ds3_row:
        return normalize_text(ds3_row.get("what_closes_it"))
    if ds1_row:
        return normalize_text(str(ds1_row.get("challenge_capsule_matched", "")).replace("_", " "))
    return normalize_text(str(primary_capsule_id or "unassigned challenge capsule").replace("_", " "))


def build_regime_view(ds4_row: dict | None, ds3_row: dict | None, lane_row: dict, metadata: dict) -> str:
    if ds4_row:
        return normalize_text(ds4_row.get("instrument_assumed"))
    if ds3_row:
        return normalize_text(ds3_row.get("likely_market_stage"))
    category = metadata.get("primary_category") or "unknown domain"
    return f"{lane_row['top_lane']} dominant in {category}"


def build_stranding_view(ds4_row: dict | None, ds3_row: dict | None, ds1_row: dict | None, lane_row: dict) -> str:
    if ds4_row:
        return normalize_text(ds4_row.get("why_stranded_then"))
    if ds3_row:
        return normalize_text(ds3_row.get("why_persists"))
    if ds1_row:
        return normalize_text(ds1_row.get("why_far_from_realized"))
    return f"No explicit DS stranding narrative yet; paper inherits only lane-level evidence from {lane_row['top_lane']}."


def build_genericity_penalty(lane_row: dict, ds1_row: dict | None) -> float:
    penalty = 0.12 if lane_row["positive_lane_count"] <= 1 else 0.0
    if ds1_row and ds1_row.get("outside_obvious_qfin_discourse"):
        penalty = max(0.0, penalty - 0.05)
    return penalty


def build_rarity_bonus(lane_row: dict, lane_prevalence: dict[str, int]) -> float:
    max_count = max(lane_prevalence.values()) if lane_prevalence else 1
    lane_count = lane_prevalence.get(lane_row["top_lane"], max_count)
    rarity = 1.0 - (lane_count / max_count)
    # @context decision -- S29 proved market-design is strategically important but numerically rare.
    # S30 therefore gives the unified score a lane-rarity bonus so the canonical ranking does not
    # collapse back to the most common participant-pathology or settlement rows by sheer volume.
    return max(0.0, 0.15 * rarity)


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    capsules_payload = load_yaml(Path(args.challenge_capsules_path).resolve(), {"capsules": []})
    capsule_defaults = load_capsule_defaults(capsules_payload)
    ds1_rows = load_jsonl(reports_dir / "ds1-translation-gap-candidates.jsonl")
    ds3_rows = load_jsonl(reports_dir / "ds3-early-market-ledger.jsonl")
    ds4_rows = load_jsonl(reports_dir / "ds4-stranded-ledger.jsonl")
    ds5_rows = load_jsonl(reports_dir / "ds5-holdout-echo-report.jsonl")

    ds1_by_paper = map_by_key(ds1_rows, "paper_id")
    ds3_by_paper = map_by_key(ds3_rows, "paper_id")
    ds4_by_paper = map_by_key(ds4_rows, "paper_id")
    ds5_by_paper = map_by_key(ds5_rows, "candidate_paper_id")

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_diamond_scores_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "diamond_scores",
            "started",
            {"lane_score_run_id": args.lane_score_run_id, "membership_run_id": args.membership_run_id},
        )
        lane_rows = fetch_lane_rows(connection, args.lane_score_run_id)
        if not lane_rows:
            raise SystemExit(f"no diamond_lane_scores rows found for run_id={args.lane_score_run_id}")
        paper_metadata = fetch_paper_metadata(connection)
        lane_prevalence = {lane: 0 for lane in LANES}
        for row in lane_rows:
            if row["top_lane_score"] > 0.05:
                lane_prevalence[row["top_lane"]] += 1

        connection.execute("DELETE FROM diamond_scores WHERE run_id = ?", (args.run_id,))
        serialized_rows = []
        for lane_row in lane_rows:
            paper_id = lane_row["paper_id"]
            feature_json = lane_row["feature_json"]
            ds1_row = ds1_by_paper.get(paper_id)
            ds3_row = ds3_by_paper.get(paper_id)
            ds4_row = ds4_by_paper.get(paper_id)
            ds5_row = ds5_by_paper.get(paper_id)

            challenge_affinity_score = normalize_challenge_affinity(
                float((ds1_row or {}).get("support", {}).get("challenge_affinity", 0.0))
            )
            positive_anchor_affinity_score = normalize_positive_affinity(
                max(
                    float((ds1_row or {}).get("support", {}).get("operator_affinity", 0.0)),
                    lane_row["top_lane_score"],
                )
            )
            negative_anchor_affinity_score = normalize_negative_affinity(
                float((ds1_row or {}).get("support", {}).get("negative_penalty", 0.0))
            )
            translation_gap_score = normalize_translation_gap(float((ds1_row or {}).get("translation_gap_score", 0.0)))
            stranding_score = max(
                lane_row["stranded_qfin_score"],
                min(1.0, float((ds4_row or {}).get("resurfacing_score", 0.0)) / 0.45),
            )
            bridge_score = max_component_score(feature_json, "bridge")
            composition_score = max_component_score(feature_json, "composition")
            holdout_echo_score = normalize_holdout(
                (ds5_row or {}).get("echo_verdict"),
                float((ds5_row or {}).get("top_echo_score", 0.0)),
            )
            transition_state_score = lane_row["transition_state_score"]
            genericity_penalty_score = build_genericity_penalty(lane_row, ds1_row)
            realized_market_leakage_penalty_score = normalize_realized_penalty(
                float((ds1_row or {}).get("support", {}).get("realized_penalty", 0.0))
            )
            lane_rarity_bonus = build_rarity_bonus(lane_row, lane_prevalence)

            diamond_score = min(
                2.0,
                0.18 * translation_gap_score
                + 0.14 * challenge_affinity_score
                + 0.14 * positive_anchor_affinity_score
                + 0.10 * bridge_score
                + 0.10 * composition_score
                + 0.10 * stranding_score
                + 0.08 * holdout_echo_score
                + 0.10 * transition_state_score
                + 0.10 * lane_row["top_lane_score"]
                + lane_rarity_bonus
                - 0.08 * negative_anchor_affinity_score
                - genericity_penalty_score
                - 0.10 * realized_market_leakage_penalty_score,
            )

            primary_capsule_id = choose_primary_capsule(lane_row, ds1_row, capsule_defaults)
            metadata = paper_metadata.get(paper_id, {})
            problem_view = build_problem_view(ds4_row, ds3_row, ds1_row, lane_row)
            mechanism_view = build_mechanism_view(ds4_row, ds3_row, ds1_row, primary_capsule_id)
            regime_view = build_regime_view(ds4_row, ds3_row, lane_row, metadata)
            # @context decision -- v2 requires every promoted candidate to expose the hidden
            # narrative that used to live only in DS reports. The representation views therefore
            # prefer DS4, then DS3, then DS1 evidence, so downstream stages always inherit the most
            # actionable explanation available instead of falling back to raw titles or lane ids.
            stranding_view = build_stranding_view(ds4_row, ds3_row, ds1_row, lane_row)

            row_feature_json = {
                "lane_feature_json": feature_json,
                "source_rows": {
                    "ds1": ds1_row,
                    "ds3": ds3_row,
                    "ds4": ds4_row,
                    "ds5": ds5_row,
                },
            }

            connection.execute(
                """
                INSERT INTO diamond_scores (
                  run_id, paper_id, lane_score_run_id, membership_run_id, score_version, diamond_score,
                  top_lane, top_lane_score, primary_capsule_id, challenge_affinity_score,
                  positive_anchor_affinity_score, negative_anchor_affinity_score, translation_gap_score,
                  stranding_score, bridge_score, composition_score, holdout_echo_score,
                  transition_state_score, genericity_penalty_score, realized_market_leakage_penalty_score,
                  lane_rarity_bonus, positive_lane_count, problem_view, mechanism_view, regime_view,
                  stranding_view, feature_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    args.run_id,
                    paper_id,
                    args.lane_score_run_id,
                    args.membership_run_id,
                    "s30-v1",
                    diamond_score,
                    lane_row["top_lane"],
                    lane_row["top_lane_score"],
                    primary_capsule_id,
                    challenge_affinity_score,
                    positive_anchor_affinity_score,
                    negative_anchor_affinity_score,
                    translation_gap_score,
                    stranding_score,
                    bridge_score,
                    composition_score,
                    holdout_echo_score,
                    transition_state_score,
                    genericity_penalty_score,
                    realized_market_leakage_penalty_score,
                    lane_rarity_bonus,
                    lane_row["positive_lane_count"],
                    problem_view,
                    mechanism_view,
                    regime_view,
                    stranding_view,
                    json.dumps(row_feature_json, sort_keys=True),
                ),
            )

            serialized_rows.append(
                {
                    "paper_id": paper_id,
                    "title": metadata.get("title"),
                    "primary_category": metadata.get("primary_category"),
                    "published_at": metadata.get("published_at"),
                    "diamond_score": round(diamond_score, 6),
                    "top_lane": lane_row["top_lane"],
                    "top_lane_score": round(lane_row["top_lane_score"], 6),
                    "primary_capsule_id": primary_capsule_id,
                    "problem_view": problem_view,
                    "mechanism_view": mechanism_view,
                    "regime_view": regime_view,
                    "stranding_view": stranding_view,
                    "challenge_affinity_score": round(challenge_affinity_score, 6),
                    "translation_gap_score": round(translation_gap_score, 6),
                    "holdout_echo_score": round(holdout_echo_score, 6),
                    "lane_rarity_bonus": round(lane_rarity_bonus, 6),
                }
            )

        serialized_rows.sort(key=lambda row: row["diamond_score"], reverse=True)
        top_rows = serialized_rows[: args.top_k]
        (output_dir / "diamond_score_top.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in top_rows),
            encoding="utf-8",
        )

        top_20 = top_rows[:20]
        top_20_lane_counts = {}
        for row in top_20:
            top_20_lane_counts[row["top_lane"]] = top_20_lane_counts.get(row["top_lane"], 0) + 1
        metrics = {
            "run_id": args.run_id,
            "scored_papers": len(serialized_rows),
            "top_20_lane_counts": dict(sorted(top_20_lane_counts.items())),
            "top_20_lane_diversity": len(top_20_lane_counts),
            "transition_state_share_in_top_20": round(
                (top_20_lane_counts.get("transition_state", 0) / len(top_20)) if top_20 else 0.0,
                6,
            ),
            "top_ranked_paper_id": top_rows[0]["paper_id"] if top_rows else None,
            "top_ranked_top_lane": top_rows[0]["top_lane"] if top_rows else None,
            "market_design_count_in_top_20": top_20_lane_counts.get("market_design", 0),
        }
        (output_dir / "diamond_score_metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        log_run_event(connection, args.run_id, "diamond_scores", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
