#!/usr/bin/env python3

import argparse
import json
import sqlite3
from collections import defaultdict
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

CANONICAL_LANES = (
    "transition_state",
    "market_design",
    "settlement_resolution",
    "participant_pathologies",
    "state_graph",
    "stranded_qfin",
)
EARLY_MARKET_LANES = (
    "market_design",
    "settlement_resolution",
    "participant_pathologies",
    "state_graph",
)
AUXILIARY_LANES = {"lifecycle"}


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize canonical six-lane diamond discovery scores.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="lane-score-materialization-20260329")
    parser.add_argument("--membership-run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--probe-run-id", default="probe-materialization-20260328-broadened")
    parser.add_argument("--bridge-run-id", default="bridge-materialization-20260328-broadened")
    parser.add_argument("--composition-run-id", default="composition-materialization-20260328-broadened")
    parser.add_argument("--transition-score-run-id", default="transition-state-score-materialization-20260328")
    parser.add_argument("--stranded-run-id", default="stranded-resurfacing-materialization-20260328")
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
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def ensure_diamond_lane_scores_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS diamond_lane_scores (
          run_id TEXT NOT NULL,
          paper_id TEXT NOT NULL,
          membership_run_id TEXT NOT NULL,
          probe_run_id TEXT NOT NULL,
          bridge_run_id TEXT NOT NULL,
          composition_run_id TEXT NOT NULL,
          transition_score_run_id TEXT NOT NULL,
          stranded_run_id TEXT NOT NULL,
          score_version TEXT NOT NULL,
          transition_state_score REAL NOT NULL,
          market_design_score REAL NOT NULL,
          settlement_resolution_score REAL NOT NULL,
          participant_pathologies_score REAL NOT NULL,
          state_graph_score REAL NOT NULL,
          stranded_qfin_score REAL NOT NULL,
          lifecycle_aux_score REAL NOT NULL DEFAULT 0,
          top_lane TEXT NOT NULL,
          top_lane_score REAL NOT NULL,
          positive_lane_count INTEGER NOT NULL,
          feature_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, paper_id),
          FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_diamond_lane_scores_run_rank
        ON diamond_lane_scores(run_id, top_lane_score DESC, paper_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_diamond_lane_scores_run_lane
        ON diamond_lane_scores(run_id, top_lane)
        """
    )


def fetch_discovery_ids(connection: sqlite3.Connection, membership_run_id: str) -> set[str]:
    rows = connection.execute(
        """
        SELECT paper_id
        FROM corpus_memberships
        WHERE run_id = ?
          AND corpus_id = 'discovery'
        """,
        (membership_run_id,),
    ).fetchall()
    if not rows:
        raise SystemExit(f"no discovery memberships found for run_id={membership_run_id}")
    return {row["paper_id"] for row in rows}


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


def normalize_bridge_score(raw_score: float) -> float:
    return min(1.0, max(0.0, raw_score) / 3.0)


def normalize_composition_score(raw_score: float) -> float:
    return min(1.0, max(0.0, raw_score) / 3.5)


def normalize_probe_score(raw_score: float) -> float:
    raw_score = max(0.0, raw_score)
    if raw_score == 0:
        return 0.0
    return raw_score / (1.0 + raw_score)


def normalize_study_score(raw_score: float, cap: float) -> float:
    if cap <= 0:
        return 0.0
    return min(1.0, max(0.0, raw_score) / cap)


def normalize_holdout_score(verdict: str, echo_score: float) -> float:
    echo_score = max(0.0, float(echo_score or 0.0))
    if verdict == "validation":
        return min(1.0, echo_score)
    if verdict == "partial":
        return min(1.0, 0.6 * echo_score)
    return 0.0


def canonical_lane(lane: str | None) -> str | None:
    if lane in CANONICAL_LANES:
        return lane
    if lane in AUXILIARY_LANES:
        return lane
    return None


def build_capsule_maps(capsules_payload: dict) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, str]]:
    anchor_to_lanes: dict[str, set[str]] = defaultdict(set)
    pattern_to_lanes: dict[str, set[str]] = defaultdict(set)
    capsule_to_lane: dict[str, str] = {}
    for capsule in capsules_payload.get("capsules", []):
        lane = canonical_lane(capsule.get("lane"))
        if lane is None:
            continue
        capsule_to_lane[capsule["capsule_id"]] = lane
        for anchor_id in capsule.get("anchor_ids", []):
            anchor_to_lanes[anchor_id].add(lane)
        for pattern_id in capsule.get("pattern_ids", []):
            pattern_to_lanes[pattern_id].add(lane)
        for pattern_id in capsule.get("far_realized_patterns", []):
            pattern_to_lanes[pattern_id].add(lane)
    return anchor_to_lanes, pattern_to_lanes, capsule_to_lane


def empty_lane_components() -> dict[str, dict]:
    return {
        lane: {
            "operator_score": 0.0,
            "probe_score": 0.0,
            "study_score": 0.0,
            "holdout_score": 0.0,
            "evidence_refs": [],
        }
        for lane in (*CANONICAL_LANES, "lifecycle")
    }


def note_component(components: dict, paper_id: str, lane: str, component_key: str, score: float, ref: dict) -> None:
    if paper_id not in components:
        return
    if lane not in components[paper_id]:
        return
    lane_components = components[paper_id][lane]
    lane_components[component_key] = max(lane_components[component_key], score)
    if score > 0:
        lane_components["evidence_refs"].append(ref)


def apply_operator_rows(
    connection: sqlite3.Connection,
    run_id: str,
    table_name: str,
    score_column: str,
    source_kind: str,
    anchor_to_lanes: dict[str, set[str]],
    components: dict[str, dict],
) -> None:
    rows = connection.execute(
        f"""
        SELECT source_anchor_id, target_anchor_id, paper_id, {score_column} AS score
        FROM {table_name}
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    normalizer = normalize_bridge_score if source_kind == "bridge" else normalize_composition_score
    for row in rows:
        lanes = set(anchor_to_lanes.get(row["source_anchor_id"], set()))
        lanes.update(anchor_to_lanes.get(row["target_anchor_id"], set()))
        score = normalizer(float(row["score"] or 0.0))
        for lane in lanes:
            note_component(
                components,
                row["paper_id"],
                lane,
                "operator_score",
                score,
                {
                    "source": source_kind,
                    "anchor_pair": [row["source_anchor_id"], row["target_anchor_id"]],
                    "score": score,
                },
            )


def apply_probe_rows(
    connection: sqlite3.Connection,
    run_id: str,
    pattern_to_lanes: dict[str, set[str]],
    components: dict[str, dict],
) -> None:
    rows = connection.execute(
        """
        SELECT tv.paper_id, ph.pattern_id, MAX(ph.score) AS score
        FROM probe_hits ph
        JOIN text_views tv
          ON tv.view_id = ph.view_id
        WHERE ph.run_id = ?
        GROUP BY tv.paper_id, ph.pattern_id
        """,
        (run_id,),
    ).fetchall()
    for row in rows:
        lanes = pattern_to_lanes.get(row["pattern_id"], set())
        score = normalize_probe_score(float(row["score"] or 0.0))
        for lane in lanes:
            note_component(
                components,
                row["paper_id"],
                lane,
                "probe_score",
                score,
                {"source": "probe", "pattern_id": row["pattern_id"], "score": score},
            )


def apply_transition_scores(connection: sqlite3.Connection, run_id: str, components: dict[str, dict]) -> None:
    rows = connection.execute(
        """
        SELECT paper_id, transition_state_score
        FROM transition_state_scores
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    for row in rows:
        score = max(0.0, float(row["transition_state_score"] or 0.0))
        note_component(
            components,
            row["paper_id"],
            "transition_state",
            "operator_score",
            score,
            {"source": "transition_state_scores", "score": score},
        )


def apply_stranded_scores(connection: sqlite3.Connection, run_id: str, components: dict[str, dict]) -> None:
    rows = connection.execute(
        """
        SELECT paper_id, resurfacing_score
        FROM stranded_resurfacing_candidates
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    for row in rows:
        score = normalize_study_score(float(row["resurfacing_score"] or 0.0), 0.45)
        note_component(
            components,
            row["paper_id"],
            "stranded_qfin",
            "operator_score",
            score,
            {"source": "stranded_resurfacing_candidates", "score": score},
        )


def apply_ds1_rows(rows: list[dict], capsule_to_lane: dict[str, str], components: dict[str, dict]) -> None:
    for row in rows:
        lane = capsule_to_lane.get(row.get("challenge_capsule_matched"))
        if lane is None:
            continue
        score = normalize_study_score(float(row.get("translation_gap_score") or 0.0), 7.0)
        if row.get("outside_obvious_qfin_discourse"):
            score = min(1.0, score + 0.1)
        note_component(
            components,
            row["paper_id"],
            lane,
            "study_score",
            score,
            {
                "source": "ds1",
                "challenge_capsule_matched": row.get("challenge_capsule_matched"),
                "translation_kind": row.get("translation_kind"),
                "score": score,
            },
        )


def apply_ds3_rows(rows: list[dict], components: dict[str, dict]) -> None:
    for row in rows:
        lane = canonical_lane(row.get("lane_family"))
        if lane is None:
            continue
        score = normalize_study_score(float(row.get("early_market_score") or 0.0), 5.0)
        note_component(
            components,
            row["paper_id"],
            lane,
            "study_score",
            score,
            {"source": "ds3", "rank": row.get("rank"), "score": score},
        )


def apply_ds4_rows(rows: list[dict], components: dict[str, dict]) -> None:
    for row in rows:
        score = normalize_study_score(float(row.get("resurfacing_score") or 0.0), 0.45)
        if row.get("executable_research_task"):
            score = min(1.0, score + 0.1)
        note_component(
            components,
            row["paper_id"],
            "stranded_qfin",
            "study_score",
            score,
            {"source": "ds4", "rescue_family": row.get("rescue_family"), "score": score},
        )


def apply_ds5_rows(rows: list[dict], components: dict[str, dict]) -> None:
    for row in rows:
        lane = canonical_lane(row.get("candidate_family"))
        if lane is None:
            continue
        score = normalize_holdout_score(row.get("echo_verdict"), float(row.get("top_echo_score") or 0.0))
        note_component(
            components,
            row["candidate_paper_id"],
            lane,
            "holdout_score",
            score,
            {
                "source": "ds5",
                "echo_verdict": row.get("echo_verdict"),
                "echo_score": row.get("top_echo_score"),
            },
        )


def finalize_lane_row(paper_id: str, lane_components: dict) -> dict:
    raw_scores = {}
    for lane in CANONICAL_LANES:
        components = lane_components[lane]
        raw_scores[lane] = min(
            1.0,
            0.45 * components["operator_score"]
            + 0.20 * components["probe_score"]
            + 0.25 * components["study_score"]
            + 0.10 * components["holdout_score"],
        )

    lifecycle_aux_score = min(
        1.0,
        0.4 * lane_components["lifecycle"]["probe_score"]
        + 0.6 * lane_components["lifecycle"]["study_score"],
    )
    # @context decision -- v2 keeps lifecycle / professionalization cues because they are useful
    # early-market evidence, but the canonical lane set is only six. We therefore treat lifecycle
    # as an auxiliary boost that strengthens the best non-transition early-market lane for a paper
    # instead of publishing a seventh top-level family and drifting away from the user-defined
    # objective.
    if lifecycle_aux_score > 0:
        best_early_lane = max(EARLY_MARKET_LANES, key=lambda lane: raw_scores[lane])
        if raw_scores[best_early_lane] > 0:
            raw_scores[best_early_lane] = min(1.0, raw_scores[best_early_lane] + 0.2 * lifecycle_aux_score)

    top_lane = max(CANONICAL_LANES, key=lambda lane: raw_scores[lane])
    positive_lane_count = sum(1 for lane in CANONICAL_LANES if raw_scores[lane] > 0.05)
    feature_json = {
        "lane_components": lane_components,
        "lane_scores": raw_scores,
        "lifecycle_aux_score": lifecycle_aux_score,
    }
    return {
        "paper_id": paper_id,
        "transition_state_score": raw_scores["transition_state"],
        "market_design_score": raw_scores["market_design"],
        "settlement_resolution_score": raw_scores["settlement_resolution"],
        "participant_pathologies_score": raw_scores["participant_pathologies"],
        "state_graph_score": raw_scores["state_graph"],
        "stranded_qfin_score": raw_scores["stranded_qfin"],
        "lifecycle_aux_score": lifecycle_aux_score,
        "top_lane": top_lane,
        "top_lane_score": raw_scores[top_lane],
        "positive_lane_count": positive_lane_count,
        "feature_json": feature_json,
    }


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    capsules_payload = load_yaml(Path(args.challenge_capsules_path).resolve(), {"capsules": []})
    anchor_to_lanes, pattern_to_lanes, capsule_to_lane = build_capsule_maps(capsules_payload)

    ds1_rows = load_jsonl(reports_dir / "ds1-translation-gap-candidates.jsonl")
    ds3_rows = load_jsonl(reports_dir / "ds3-early-market-ledger.jsonl")
    ds4_rows = load_jsonl(reports_dir / "ds4-stranded-ledger.jsonl")
    ds5_rows = load_jsonl(reports_dir / "ds5-holdout-echo-report.jsonl")

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_diamond_lane_scores_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "diamond_lane_scores",
            "started",
            {
                "membership_run_id": args.membership_run_id,
                "probe_run_id": args.probe_run_id,
                "bridge_run_id": args.bridge_run_id,
                "composition_run_id": args.composition_run_id,
                "transition_score_run_id": args.transition_score_run_id,
                "stranded_run_id": args.stranded_run_id,
            },
        )
        discovery_ids = fetch_discovery_ids(connection, args.membership_run_id)
        paper_metadata = fetch_paper_metadata(connection)
        components = {paper_id: empty_lane_components() for paper_id in discovery_ids}

        apply_operator_rows(
            connection,
            args.bridge_run_id,
            "bridge_candidates",
            "bridge_score",
            "bridge",
            anchor_to_lanes,
            components,
        )
        apply_operator_rows(
            connection,
            args.composition_run_id,
            "composition_candidates",
            "composition_score",
            "composition",
            anchor_to_lanes,
            components,
        )
        apply_probe_rows(connection, args.probe_run_id, pattern_to_lanes, components)
        apply_transition_scores(connection, args.transition_score_run_id, components)
        apply_stranded_scores(connection, args.stranded_run_id, components)
        apply_ds1_rows(ds1_rows, capsule_to_lane, components)
        apply_ds3_rows(ds3_rows, components)
        apply_ds4_rows(ds4_rows, components)
        apply_ds5_rows(ds5_rows, components)

        connection.execute("DELETE FROM diamond_lane_scores WHERE run_id = ?", (args.run_id,))
        rows = []
        for paper_id in sorted(discovery_ids):
            row = finalize_lane_row(paper_id, components[paper_id])
            rows.append(row)
            connection.execute(
                """
                INSERT INTO diamond_lane_scores (
                  run_id, paper_id, membership_run_id, probe_run_id, bridge_run_id, composition_run_id,
                  transition_score_run_id, stranded_run_id, score_version, transition_state_score,
                  market_design_score, settlement_resolution_score, participant_pathologies_score,
                  state_graph_score, stranded_qfin_score, lifecycle_aux_score, top_lane, top_lane_score,
                  positive_lane_count, feature_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    args.run_id,
                    paper_id,
                    args.membership_run_id,
                    args.probe_run_id,
                    args.bridge_run_id,
                    args.composition_run_id,
                    args.transition_score_run_id,
                    args.stranded_run_id,
                    "s29-v1",
                    row["transition_state_score"],
                    row["market_design_score"],
                    row["settlement_resolution_score"],
                    row["participant_pathologies_score"],
                    row["state_graph_score"],
                    row["stranded_qfin_score"],
                    row["lifecycle_aux_score"],
                    row["top_lane"],
                    row["top_lane_score"],
                    row["positive_lane_count"],
                    json.dumps(row["feature_json"], sort_keys=True),
                ),
            )

        top_rows = sorted(rows, key=lambda item: (item["top_lane_score"], item["positive_lane_count"]), reverse=True)[
            : args.top_k
        ]
        top_serialized = []
        for row in top_rows:
            metadata = paper_metadata.get(row["paper_id"], {})
            top_serialized.append(
                {
                    "paper_id": row["paper_id"],
                    "title": metadata.get("title"),
                    "primary_category": metadata.get("primary_category"),
                    "published_at": metadata.get("published_at"),
                    "top_lane": row["top_lane"],
                    "top_lane_score": round(row["top_lane_score"], 6),
                    "positive_lane_count": row["positive_lane_count"],
                    "transition_state_score": round(row["transition_state_score"], 6),
                    "market_design_score": round(row["market_design_score"], 6),
                    "settlement_resolution_score": round(row["settlement_resolution_score"], 6),
                    "participant_pathologies_score": round(row["participant_pathologies_score"], 6),
                    "state_graph_score": round(row["state_graph_score"], 6),
                    "stranded_qfin_score": round(row["stranded_qfin_score"], 6),
                    "lifecycle_aux_score": round(row["lifecycle_aux_score"], 6),
                }
            )
        (output_dir / "diamond_lane_score_top.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in top_serialized),
            encoding="utf-8",
        )

        positive_by_lane = {
            lane: sum(1 for row in rows if row[f"{lane}_score"] > 0.05)
            for lane in CANONICAL_LANES
        }
        top_by_lane = {}
        for lane in CANONICAL_LANES:
            best = max(rows, key=lambda item: item[f"{lane}_score"])
            metadata = paper_metadata.get(best["paper_id"], {})
            top_by_lane[lane] = {
                "paper_id": best["paper_id"],
                "title": metadata.get("title"),
                "score": round(best[f"{lane}_score"], 6),
            }
        top20 = top_serialized[:20]
        top20_lane_counts = defaultdict(int)
        for row in top20:
            top20_lane_counts[row["top_lane"]] += 1
        metrics = {
            "run_id": args.run_id,
            "scored_papers": len(rows),
            "positive_score_papers_by_lane": positive_by_lane,
            "top_by_lane": top_by_lane,
            "top_20_lane_counts": dict(sorted(top20_lane_counts.items())),
            "top_20_lane_diversity": len(top20_lane_counts),
            "transition_state_share_in_top_20": round(
                (top20_lane_counts.get("transition_state", 0) / len(top20)) if top20 else 0.0,
                6,
            ),
        }
        (output_dir / "diamond_lane_score_metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        log_run_event(connection, args.run_id, "diamond_lane_scores", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
