#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_ANCHORS_PATH = ROOT / "configs" / "anchors.yaml"
DEFAULT_PROBES_PATH = ROOT / "configs" / "probes.yaml"

TRANSITION_ANCHOR_IDS = (
    "queue_value_passive_quoting",
    "refill_lag_resiliency",
    "auction_handoff",
    "maker_retreat_inventory_stress",
    "parity_propagation_delayed_repair",
)
FAMILY_SCORE_COLUMNS = {
    "queue_value_passive_quoting": "queue_value_score",
    "refill_lag_resiliency": "refill_resiliency_score",
    "auction_handoff": "auction_handoff_score",
    "maker_retreat_inventory_stress": "maker_retreat_score",
    "parity_propagation_delayed_repair": "parity_repair_score",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize canonical transition-state paper scores.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="transition-state-score-materialization-20260328")
    parser.add_argument("--membership-run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--probe-run-id", default="probe-materialization-20260328-transition-state")
    parser.add_argument("--anchors-path", default=str(DEFAULT_ANCHORS_PATH))
    parser.add_argument("--probes-path", default=str(DEFAULT_PROBES_PATH))
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--top-k", type=int, default=50)
    return parser.parse_args()


def load_yaml(path: Path, default):
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def ensure_transition_state_scores_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS transition_state_scores (
          run_id TEXT NOT NULL,
          paper_id TEXT NOT NULL,
          membership_run_id TEXT NOT NULL,
          probe_run_id TEXT NOT NULL,
          score_version TEXT NOT NULL,
          transition_state_score REAL NOT NULL,
          queue_value_score REAL NOT NULL,
          refill_resiliency_score REAL NOT NULL,
          auction_handoff_score REAL NOT NULL,
          maker_retreat_score REAL NOT NULL,
          parity_repair_score REAL NOT NULL,
          sparse_component_score REAL NOT NULL,
          proximity_component_score REAL NOT NULL,
          family_count INTEGER NOT NULL,
          feature_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (run_id, paper_id),
          FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_transition_state_scores_run_score
        ON transition_state_scores(run_id, transition_state_score DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_transition_state_scores_run_paper
        ON transition_state_scores(run_id, paper_id)
        """
    )


def normalize_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def keyword_match_details(text: str, anchor: dict) -> tuple[list[str], float]:
    matched = []
    for keyword in anchor.get("keywords", []):
        if keyword.lower() in text:
            matched.append(keyword)
    threshold = max(int(anchor.get("min_keyword_hits") or 1) + 1, 3)
    sparse_score = min(1.0, len(matched) / threshold)
    return matched, sparse_score


def normalize_probe_score(raw_score: float) -> float:
    if raw_score <= 0:
        return 0.0
    return raw_score / (1.0 + raw_score)


def load_transition_anchor_defs(anchors_payload: dict) -> list[dict]:
    by_id = {anchor["anchor_id"]: anchor for anchor in anchors_payload.get("anchors", [])}
    return [by_id[anchor_id] for anchor_id in TRANSITION_ANCHOR_IDS if anchor_id in by_id]


def load_family_pattern_map(probes_payload: dict) -> dict[str, list[str]]:
    mapping = {anchor_id: [] for anchor_id in TRANSITION_ANCHOR_IDS}
    for pattern in probes_payload.get("patterns", []):
        for anchor_id in pattern.get("include", []):
            if anchor_id in mapping:
                mapping[anchor_id].append(pattern["pattern_id"])
    return mapping


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
        raise SystemExit(f"no discovery corpus memberships found for run_id={membership_run_id}")
    return {row["paper_id"] for row in rows}


def fetch_probe_support(
    connection: sqlite3.Connection, probe_run_id: str, family_pattern_map: dict[str, list[str]]
) -> dict[str, dict[str, dict]]:
    support = {anchor_id: {} for anchor_id in family_pattern_map}
    for anchor_id, pattern_ids in family_pattern_map.items():
        if not pattern_ids:
            continue
        placeholders = ",".join("?" for _ in pattern_ids)
        rows = connection.execute(
            f"""
            SELECT tv.paper_id, ph.pattern_id, ph.score, ph.rank
            FROM probe_hits ph
            JOIN text_views tv
              ON tv.view_id = ph.view_id
            WHERE ph.run_id = ?
              AND ph.pattern_id IN ({placeholders})
            ORDER BY tv.paper_id, ph.score DESC, ph.rank ASC
            """,
            (probe_run_id, *pattern_ids),
        ).fetchall()
        for row in rows:
            current = support[anchor_id].get(row["paper_id"])
            payload = {
                "pattern_id": row["pattern_id"],
                "raw_score": float(row["score"]),
                "rank": int(row["rank"]),
            }
            if current is None or payload["raw_score"] > current["raw_score"]:
                support[anchor_id][row["paper_id"]] = payload
    return support


def build_score_rows(
    connection: sqlite3.Connection,
    membership_run_id: str,
    probe_run_id: str,
    anchor_defs: list[dict],
    family_pattern_map: dict[str, list[str]],
) -> list[dict]:
    discovery_ids = fetch_discovery_ids(connection, membership_run_id)
    probe_support = fetch_probe_support(connection, probe_run_id, family_pattern_map)
    papers = connection.execute(
        """
        SELECT paper_id, title, abstract
        FROM papers
        ORDER BY paper_id
        """
    ).fetchall()
    score_rows = []
    for row in papers:
        paper_id = row["paper_id"]
        if paper_id not in discovery_ids:
            continue
        text = normalize_text(f"{row['title'] or ''}\n{row['abstract'] or ''}")
        family_scores = {}
        feature_payload = {}
        sparse_total = 0.0
        proximity_total = 0.0
        family_count = 0
        for anchor in anchor_defs:
            anchor_id = anchor["anchor_id"]
            matched_keywords, sparse_score = keyword_match_details(text, anchor)
            probe_payload = probe_support.get(anchor_id, {}).get(paper_id)
            proximity_raw = float(probe_payload["raw_score"]) if probe_payload else 0.0
            proximity_score = normalize_probe_score(proximity_raw)
            # @context decision -- S18 is intentionally continuous and auditable. It fuses sparse
            # keyword evidence from transition-state anchors with probe-hit proximity instead of
            # inventing a hidden embedding-only rank, so later operator stages can explain whether a
            # paper looks transition-state-relevant because of explicit language, latent proximity,
            # or both.
            family_score = min(1.0, 0.45 * sparse_score + 0.55 * proximity_score)
            family_scores[anchor_id] = family_score
            sparse_total += sparse_score
            proximity_total += proximity_score
            if family_score > 0:
                family_count += 1
            feature_payload[anchor_id] = {
                "matched_keywords": matched_keywords,
                "sparse_score": sparse_score,
                "probe_pattern_id": probe_payload["pattern_id"] if probe_payload else None,
                "probe_rank": probe_payload["rank"] if probe_payload else None,
                "probe_raw_score": proximity_raw,
                "proximity_score": proximity_score,
                "family_score": family_score,
            }
        sparse_component_score = sparse_total / max(1, len(anchor_defs))
        proximity_component_score = proximity_total / max(1, len(anchor_defs))
        coverage_bonus = min(0.2, 0.05 * max(0, family_count - 1))
        transition_state_score = min(
            1.0,
            (sum(family_scores.values()) / max(1, len(anchor_defs))) + coverage_bonus,
        )
        score_rows.append(
            {
                "paper_id": paper_id,
                "transition_state_score": transition_state_score,
                "family_scores": family_scores,
                "sparse_component_score": sparse_component_score,
                "proximity_component_score": proximity_component_score,
                "family_count": family_count,
                "feature_json": feature_payload,
            }
        )
    return score_rows


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    anchors_payload = load_yaml(Path(args.anchors_path).resolve(), {"anchors": []})
    probes_payload = load_yaml(Path(args.probes_path).resolve(), {"patterns": []})
    anchor_defs = load_transition_anchor_defs(anchors_payload)
    family_pattern_map = load_family_pattern_map(probes_payload)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        ensure_transition_state_scores_table(connection)
        log_run_event(
            connection,
            args.run_id,
            "transition_state_score",
            "started",
            {
                "membership_run_id": args.membership_run_id,
                "probe_run_id": args.probe_run_id,
                "anchors_path": str(Path(args.anchors_path).resolve()),
                "probes_path": str(Path(args.probes_path).resolve()),
            },
        )
        score_rows = build_score_rows(
            connection,
            args.membership_run_id,
            args.probe_run_id,
            anchor_defs,
            family_pattern_map,
        )
        connection.execute("DELETE FROM transition_state_scores WHERE run_id = ?", (args.run_id,))
        insert_rows = []
        for row in score_rows:
            insert_rows.append(
                (
                    args.run_id,
                    row["paper_id"],
                    args.membership_run_id,
                    args.probe_run_id,
                    "transition-state-v1",
                    row["transition_state_score"],
                    row["family_scores"].get("queue_value_passive_quoting", 0.0),
                    row["family_scores"].get("refill_lag_resiliency", 0.0),
                    row["family_scores"].get("auction_handoff", 0.0),
                    row["family_scores"].get("maker_retreat_inventory_stress", 0.0),
                    row["family_scores"].get("parity_propagation_delayed_repair", 0.0),
                    row["sparse_component_score"],
                    row["proximity_component_score"],
                    row["family_count"],
                    json.dumps(row["feature_json"], sort_keys=True),
                )
            )
        connection.executemany(
            """
            INSERT INTO transition_state_scores (
              run_id,
              paper_id,
              membership_run_id,
              probe_run_id,
              score_version,
              transition_state_score,
              queue_value_score,
              refill_resiliency_score,
              auction_handoff_score,
              maker_retreat_score,
              parity_repair_score,
              sparse_component_score,
              proximity_component_score,
              family_count,
              feature_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows,
        )

        ranked = sorted(
            score_rows,
            key=lambda item: (-item["transition_state_score"], -item["family_count"], item["paper_id"]),
        )[: args.top_k]
        top_path = output_dir / "transition_state_score_top.jsonl"
        with top_path.open("w", encoding="utf-8") as handle:
            for item in ranked:
                handle.write(json.dumps(item, sort_keys=True) + "\n")

        metrics = {
            "run_id": args.run_id,
            "membership_run_id": args.membership_run_id,
            "probe_run_id": args.probe_run_id,
            "scored_papers": len(score_rows),
            "positive_score_papers": sum(1 for row in score_rows if row["transition_state_score"] > 0),
            "top_score": max((row["transition_state_score"] for row in score_rows), default=0.0),
            "family_positive_papers": {
                column: sum(1 for row in score_rows if row["family_scores"].get(anchor_id, 0.0) > 0)
                for anchor_id, column in FAMILY_SCORE_COLUMNS.items()
            },
        }
        metrics_path = output_dir / "transition_state_score_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        log_run_event(
            connection,
            args.run_id,
            "transition_state_score",
            "completed",
            {"metrics_path": str(metrics_path), **metrics},
        )
        connection.commit()
    finally:
        connection.close()

    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
