#!/usr/bin/env python3

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

from sqlite_vec_adapter import connect as connect_vec_store


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_ANCHORS_PATH = ROOT / "configs" / "anchors.yaml"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize canonical negative-space candidates from negative anchors.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="negative-space-materialization-20260328")
    parser.add_argument("--embedding-run-id", default="view-embeddings-materialization-20260328")
    parser.add_argument("--embedding-metrics-path", default=None)
    parser.add_argument("--vec-db-path", default=None)
    parser.add_argument("--anchors-path", default=str(DEFAULT_ANCHORS_PATH))
    parser.add_argument("--membership-run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--stranding-run-id", default="stranding-score-materialization-20260328")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--top-k", type=int, default=25)
    parser.add_argument("--stranding_penalty_weight", type=float, default=0.10)
    return parser.parse_args()


def load_yaml(path: Path, default):
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_embedding_metrics(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def table_name_for_space(space_name: str, dims: int) -> str:
    return f"vec_{space_name}_{dims}".replace("-", "_")


def vector_from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def load_space_vectors(vec_connection: sqlite3.Connection, table_name: str) -> dict[int, np.ndarray]:
    rows = vec_connection.execute(f"SELECT rowid, embedding FROM {table_name} ORDER BY rowid").fetchall()
    return {int(rowid): vector_from_blob(blob) for rowid, blob in rows}


def normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def resolve_anchor_paper_ids(connection: sqlite3.Connection, anchor: dict) -> list[str]:
    explicit = list(anchor.get("paper_ids", []))
    patterns = anchor.get("family_patterns", [])
    if not patterns:
        return explicit
    resolved = set(explicit)
    for pattern in patterns:
        rows = connection.execute(
            """
            SELECT DISTINCT mi.paper_id
            FROM mechanism_instances mi
            JOIN candidate_family_members cfm
              ON cfm.candidate_mechanism_instance_id = mi.mechanism_instance_id
            JOIN candidate_families cf
              ON cf.candidate_family_id = cfm.candidate_family_id
            WHERE lower(cf.family_name) LIKE ?
            """,
            (f"%{pattern.lower()}%",),
        ).fetchall()
        resolved.update(row["paper_id"] for row in rows)
    return sorted(resolved)


def build_anchor_centroids(
    canonical_connection: sqlite3.Connection,
    vectors_by_view_id: dict[int, np.ndarray],
    view_type: str,
    anchors_payload: dict,
) -> tuple[dict[str, np.ndarray], dict[str, set[str]]]:
    centroids = {}
    seed_sets = {}
    for anchor in anchors_payload.get("anchors", []):
        paper_ids = resolve_anchor_paper_ids(canonical_connection, anchor)
        if not paper_ids:
            continue
        seed_sets[anchor["anchor_id"]] = set(paper_ids)
        placeholders = ",".join("?" for _ in paper_ids)
        rows = canonical_connection.execute(
            f"""
            SELECT view_id
            FROM text_views
            WHERE view_type = ?
              AND paper_id IN ({placeholders})
            """,
            (view_type, *paper_ids),
        ).fetchall()
        vectors = [vectors_by_view_id[int(row["view_id"])] for row in rows if int(row["view_id"]) in vectors_by_view_id]
        if vectors:
            centroids[anchor["anchor_id"]] = normalize(np.mean(np.stack(vectors), axis=0))
    return centroids, seed_sets


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
    return {row["paper_id"] for row in rows}


def fetch_stranding_scores(connection: sqlite3.Connection, stranding_run_id: str) -> dict[str, float]:
    rows = connection.execute(
        """
        SELECT paper_id, stranding_score
        FROM stranding_scores
        WHERE run_id = ?
        """,
        (stranding_run_id,),
    ).fetchall()
    return {row["paper_id"]: float(row["stranding_score"]) for row in rows}


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.embedding_metrics_path:
        embedding_metrics_path = Path(args.embedding_metrics_path).resolve()
    else:
        embedding_metrics_path = DEFAULT_OUTPUT_ROOT / args.embedding_run_id / "embedding_metrics.json"
    embedding_metrics = load_embedding_metrics(embedding_metrics_path)
    vec_db_path = Path(args.vec_db_path).resolve() if args.vec_db_path else Path(embedding_metrics["vec_db_path"]).resolve()
    anchors_payload = load_yaml(Path(args.anchors_path).resolve(), {"anchors": []})

    canonical_connection = sqlite3.connect(str(db_path))
    canonical_connection.row_factory = sqlite3.Row
    vec_connection = connect_vec_store(vec_db_path)
    try:
        log_run_event(
            canonical_connection,
            args.run_id,
            "negative_space",
            "started",
            {
                "embedding_run_id": args.embedding_run_id,
                "membership_run_id": args.membership_run_id,
                "stranding_run_id": args.stranding_run_id,
                "top_k": args.top_k,
            },
        )
        discovery_ids = fetch_discovery_ids(canonical_connection, args.membership_run_id)
        stranding_scores = fetch_stranding_scores(canonical_connection, args.stranding_run_id)
        canonical_connection.execute("DELETE FROM negative_space_candidates WHERE run_id = ?", (args.run_id,))

        anchors = anchors_payload.get("anchors", [])
        negative_anchor_ids = [anchor["anchor_id"] for anchor in anchors if anchor.get("anchor_type") == "negative"]

        aggregated = defaultdict(
            lambda: {
                "score": 0.0,
                "space_support": 0,
                "representative_view_id": None,
                "best_component_score": float("-inf"),
                "space_components": {},
            }
        )

        for space in embedding_metrics["spaces"]:
            table_name = space.get("table_name") or table_name_for_space(space["name"], space["dims"])
            vectors_by_view_id = load_space_vectors(vec_connection, table_name)
            if not vectors_by_view_id:
                continue

            view_rows = canonical_connection.execute(
                """
                SELECT view_id, paper_id
                FROM text_views
                WHERE view_type = ?
                ORDER BY view_id
                """,
                (space["view_type"],),
            ).fetchall()
            candidate_rows = [
                row for row in view_rows if int(row["view_id"]) in vectors_by_view_id and row["paper_id"] in discovery_ids
            ]
            if not candidate_rows:
                continue

            view_ids = [int(row["view_id"]) for row in candidate_rows]
            paper_ids = [row["paper_id"] for row in candidate_rows]
            matrix = np.stack([normalize(vectors_by_view_id[view_id]) for view_id in view_ids])

            centroids, seed_sets = build_anchor_centroids(
                canonical_connection,
                vectors_by_view_id,
                space["view_type"],
                anchors_payload,
            )
            available_negative = [anchor_id for anchor_id in negative_anchor_ids if anchor_id in centroids]
            if not available_negative:
                continue

            for negative_anchor_id in available_negative:
                sims = matrix @ centroids[negative_anchor_id]
                negative_seed_ids = seed_sets.get(negative_anchor_id, set())
                for idx, paper_id in enumerate(paper_ids):
                    # @context requirement -- Negative-space candidates must exclude the negative
                    # anchor seeds themselves. Otherwise the surface would be a tautological replay
                    # of known dead ends instead of a queryable neighborhood around them.
                    if paper_id in negative_seed_ids:
                        continue
                    stranding_score = stranding_scores.get(paper_id, 0.0)
                    negative_component = float(sims[idx]) - args.stranding_penalty_weight * stranding_score
                    if negative_component <= 0:
                        continue
                    key = (negative_anchor_id, paper_id)
                    payload = aggregated[key]
                    payload["score"] += negative_component
                    payload["space_support"] += 1
                    payload["space_components"][space["name"]] = {
                        "negative_component": round(negative_component, 6),
                        "negative_similarity": round(float(sims[idx]), 6),
                        "stranding_score": round(stranding_score, 6),
                    }
                    if negative_component > payload["best_component_score"]:
                        payload["best_component_score"] = negative_component
                        payload["representative_view_id"] = view_ids[idx]

        grouped = defaultdict(list)
        for (anchor_id, paper_id), payload in aggregated.items():
            grouped[anchor_id].append(
                {
                    "paper_id": paper_id,
                    "representative_view_id": payload["representative_view_id"],
                    "negative_space_score": round(payload["score"], 6),
                    "space_support": payload["space_support"],
                    "rationale_json": json.dumps(
                        {
                            "space_components": payload["space_components"],
                            "stranding_score": round(stranding_scores.get(paper_id, 0.0), 6),
                        },
                        sort_keys=True,
                    ),
                }
            )

        candidate_rows = []
        preview_rows = []
        for anchor_id, items in grouped.items():
            ranked = sorted(items, key=lambda item: (-item["negative_space_score"], -item["space_support"], item["paper_id"]))[: args.top_k]
            for rank, item in enumerate(ranked, start=1):
                candidate_rows.append(
                    (
                        args.run_id,
                        anchor_id,
                        item["paper_id"],
                        item["representative_view_id"],
                        item["negative_space_score"],
                        rank,
                        item["space_support"],
                        item["rationale_json"],
                    )
                )
                preview_rows.append(
                    {
                        "run_id": args.run_id,
                        "anchor_id": anchor_id,
                        "paper_id": item["paper_id"],
                        "negative_space_score": item["negative_space_score"],
                        "negative_rank": rank,
                        "space_support": item["space_support"],
                    }
                )

        canonical_connection.executemany(
            """
            INSERT INTO negative_space_candidates (
              run_id,
              anchor_id,
              paper_id,
              representative_view_id,
              negative_space_score,
              negative_rank,
              space_support,
              rationale_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            candidate_rows,
        )

        metrics = {
            "run_id": args.run_id,
            "embedding_run_id": args.embedding_run_id,
            "membership_run_id": args.membership_run_id,
            "stranding_run_id": args.stranding_run_id,
            "negative_anchor_count": len(grouped),
            "negative_space_candidate_count": len(candidate_rows),
            "anchors_with_candidates": len(grouped),
            "top_k": args.top_k,
            "top_score": max((row["negative_space_score"] for row in preview_rows), default=0.0),
        }
        metrics_path = output_dir / "negative_space_metrics.json"
        preview_path = output_dir / "negative_space.jsonl"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        preview_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in preview_rows),
            encoding="utf-8",
        )
        log_run_event(
            canonical_connection,
            args.run_id,
            "negative_space",
            "completed",
            {
                **metrics,
                "metrics_path": str(metrics_path),
                "preview_path": str(preview_path),
            },
        )
        canonical_connection.commit()
    finally:
        vec_connection.close()
        canonical_connection.close()

    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
