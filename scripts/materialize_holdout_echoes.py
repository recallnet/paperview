#!/usr/bin/env python3

import argparse
import json
import sqlite3
from array import array
from math import sqrt
from pathlib import Path

try:
    import sqlite_vec
except ImportError:  # pragma: no cover - exercised in fixture path without vec virtual tables
    sqlite_vec = None

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize holdout echo candidates for interpreted shortlist items.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="holdout-echo-materialization-20260328")
    parser.add_argument("--interpretation-run-id", default="selective-interpretation-ingestion-20260328")
    parser.add_argument("--membership-run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--embedding-run-id", default="view-embeddings-materialization-20260328")
    parser.add_argument("--embedding-metrics-path", default=None)
    parser.add_argument("--vec-db-path", default=None)
    parser.add_argument("--view-type", default="title_abs")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def connect_vec_db(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    if sqlite_vec is not None:
        connection.enable_load_extension(True)
        sqlite_vec.load(connection)
    return connection


def normalize(vector: list[float]) -> list[float]:
    norm = sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def vector_from_blob(blob: bytes) -> list[float]:
    values = array("f")
    values.frombytes(blob)
    return list(values)


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def mean_vectors(vectors: list[list[float]]) -> list[float]:
    width = len(vectors[0])
    totals = [0.0] * width
    for vector in vectors:
        for index, value in enumerate(vector):
            totals[index] += value
    count = float(len(vectors))
    return [value / count for value in totals]


def table_name_for_space(space_name: str, dims: int) -> str:
    return f"vec_{space_name}_{dims}".replace("-", "_")


def load_embedding_metrics(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_vectors_for_view_type(
    canonical_connection: sqlite3.Connection,
    vec_connection: sqlite3.Connection,
    embedding_metrics: dict,
    view_type: str,
) -> tuple[dict[str, list[float]], dict[int, str]]:
    matching_space = next(space for space in embedding_metrics["spaces"] if space["view_type"] == view_type)
    table_name = matching_space.get("table_name") or table_name_for_space(matching_space["name"], matching_space["dims"])
    vec_rows = vec_connection.execute(f"SELECT rowid, embedding FROM {table_name}").fetchall()
    vectors_by_view_id = {int(rowid): normalize(vector_from_blob(blob)) for rowid, blob in vec_rows}

    text_rows = canonical_connection.execute(
        """
        SELECT view_id, paper_id
        FROM text_views
        WHERE view_type = ?
        """,
        (view_type,),
    ).fetchall()
    vectors_by_paper_id = {}
    for row in text_rows:
        view_id = int(row["view_id"])
        if view_id in vectors_by_view_id:
            vectors_by_paper_id[row["paper_id"]] = vectors_by_view_id[view_id]
    return vectors_by_paper_id, {int(row["view_id"]): row["paper_id"] for row in text_rows}


def fetch_holdout_paper_ids(connection: sqlite3.Connection, membership_run_id: str) -> list[str]:
    rows = connection.execute(
        """
        SELECT paper_id
        FROM corpus_memberships
        WHERE run_id = ?
          AND corpus_id = 'holdout'
        ORDER BY paper_id
        """,
        (membership_run_id,),
    ).fetchall()
    return [row["paper_id"] for row in rows]


def resolve_source_paper_ids(shortlist_row: sqlite3.Row) -> list[str]:
    # @context decision -- Holdout echoes should compare later discourse against the same papers that
    # supported shortlist and review decisions. Using packet representative papers keeps echo scoring
    # anchored to reviewed evidence instead of to synthetic labels alone.
    item_type = shortlist_row["item_type"]
    if item_type == "paper":
        return [shortlist_row["item_ref"]]
    summary = json.loads(shortlist_row["summary_json"])
    return list(summary.get("representative_papers", []))


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

    canonical_connection = sqlite3.connect(str(db_path))
    canonical_connection.row_factory = sqlite3.Row
    vec_connection = connect_vec_db(vec_db_path)
    try:
        log_run_event(
            canonical_connection,
            args.run_id,
            "holdout_echo",
            "started",
            {
                "interpretation_run_id": args.interpretation_run_id,
                "membership_run_id": args.membership_run_id,
                "embedding_run_id": args.embedding_run_id,
                "view_type": args.view_type,
                "top_k": args.top_k,
            },
        )
        canonical_connection.execute("DELETE FROM holdout_echoes WHERE run_id = ?", (args.run_id,))

        vectors_by_paper_id, _ = load_vectors_for_view_type(canonical_connection, vec_connection, embedding_metrics, args.view_type)
        holdout_paper_ids = [paper_id for paper_id in fetch_holdout_paper_ids(canonical_connection, args.membership_run_id) if paper_id in vectors_by_paper_id]
        holdout_vectors = {paper_id: vectors_by_paper_id[paper_id] for paper_id in holdout_paper_ids}

        interpretation_rows = canonical_connection.execute(
            """
            SELECT
              si.shortlist_id,
              si.item_type,
              si.item_ref,
              rp.summary_json
            FROM selective_interpretations interp
            JOIN shortlist_items si
              ON si.run_id = interp.shortlist_run_id
             AND si.shortlist_id = interp.shortlist_id
            JOIN review_packets rp
              ON rp.run_id = si.packet_run_id
             AND rp.packet_kind = si.packet_kind
             AND rp.item_ref = si.packet_item_ref
            WHERE interp.run_id = ?
            ORDER BY si.shortlist_id
            """,
            (args.interpretation_run_id,),
        ).fetchall()

        echo_rows = []
        counts_by_shortlist = {}
        for row in interpretation_rows:
            source_paper_ids = [paper_id for paper_id in resolve_source_paper_ids(row) if paper_id in vectors_by_paper_id]
            if not source_paper_ids:
                continue
            # @context requirement -- The echo stage validates later discourse proximity, not direct
            # citation. A centroid over reviewed source papers lets one interpreted shortlist item
            # compare against the holdout corpus without reinterpreting every source paper separately.
            centroid = normalize(mean_vectors([vectors_by_paper_id[paper_id] for paper_id in source_paper_ids]))
            scored = []
            for holdout_paper_id, holdout_vector in holdout_vectors.items():
                score = float(dot(centroid, holdout_vector))
                scored.append((holdout_paper_id, score))
            scored.sort(key=lambda item: (-item[1], item[0]))
            top_items = scored[: args.top_k]
            counts_by_shortlist[row["shortlist_id"]] = len(top_items)
            for rank, (holdout_paper_id, score) in enumerate(top_items, start=1):
                rationale = {
                    "view_type": args.view_type,
                    "source_paper_ids": source_paper_ids,
                }
                canonical_connection.execute(
                    """
                    INSERT INTO holdout_echoes (
                      run_id,
                      interpretation_run_id,
                      shortlist_id,
                      holdout_paper_id,
                      echo_score,
                      echo_rank,
                      source_paper_ids_json,
                      rationale_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        args.run_id,
                        args.interpretation_run_id,
                        row["shortlist_id"],
                        holdout_paper_id,
                        score,
                        rank,
                        json.dumps(source_paper_ids, sort_keys=True),
                        json.dumps(rationale, sort_keys=True),
                    ),
                )
                echo_rows.append(
                    {
                        "shortlist_id": row["shortlist_id"],
                        "holdout_paper_id": holdout_paper_id,
                        "echo_score": score,
                        "echo_rank": rank,
                        "source_paper_ids": source_paper_ids,
                    }
                )

        echoes_path = output_dir / "holdout_echoes.jsonl"
        with echoes_path.open("w", encoding="utf-8") as handle:
            for item in echo_rows:
                handle.write(json.dumps(item, sort_keys=True) + "\n")

        metrics = {
            "run_id": args.run_id,
            "interpretation_run_id": args.interpretation_run_id,
            "echo_count": len(echo_rows),
            "interpreted_shortlist_count": len(interpretation_rows),
            "shortlists_with_echoes": sum(1 for count in counts_by_shortlist.values() if count > 0),
            "top_k": args.top_k,
            "view_type": args.view_type,
        }
        metrics_path = output_dir / "holdout_echo_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log_run_event(canonical_connection, args.run_id, "holdout_echo", "completed", metrics)
        canonical_connection.commit()
    finally:
        vec_connection.close()
        canonical_connection.close()


if __name__ == "__main__":
    main()
