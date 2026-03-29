#!/usr/bin/env python3

import argparse
import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize canonical review packets from canonical discovery tables.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="review-packet-materialization-20260328")
    parser.add_argument("--cluster-run-id", default="cluster-materialization-20260328")
    parser.add_argument("--bridge-run-id", default="bridge-materialization-20260328")
    parser.add_argument("--composition-run-id", default="composition-materialization-20260328")
    parser.add_argument("--transition-run-id", default="transition-state-candidate-materialization-20260328")
    parser.add_argument("--stranding-run-id", default="stranding-score-materialization-20260328")
    parser.add_argument("--membership-run-id", default="corpus-membership-materialization-20260328")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--cluster-level", default="mid")
    parser.add_argument("--top-clusters", type=int, default=6)
    parser.add_argument("--top-bridges", type=int, default=6)
    parser.add_argument("--top-compositions", type=int, default=6)
    parser.add_argument("--top-transitions", type=int, default=6)
    parser.add_argument("--top-stranded", type=int, default=6)
    return parser.parse_args()


def slugify(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return lowered or "packet"


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def write_packet(packet_dir: Path, packet_kind: str, item_ref: str, markdown: str) -> Path:
    filename = f"{packet_kind}__{slugify(item_ref)}.md"
    path = packet_dir / filename
    path.write_text(markdown, encoding="utf-8")
    return path


def fetch_cluster_packets(connection: sqlite3.Connection, cluster_run_id: str, stranding_run_id: str, level: str, limit: int):
    # @context decision -- Review packets must be deterministic because shortlist and later
    # interpretation stages will key off packet rows and disk paths. Stable tie-breaks keep packet
    # identities from drifting between reruns when scores are equal.
    rows = connection.execute(
        """
        SELECT
          c.cluster_id,
          COALESCE(c.label, c.cluster_id) AS cluster_label,
          COALESCE(c.summary, '') AS cluster_summary,
          c.size,
          AVG(COALESCE(ss.stranding_score, 0.0)) AS avg_stranding,
          MAX(COALESCE(ss.stranding_score, 0.0)) AS max_stranding
        FROM clusters c
        JOIN cluster_members cm
          ON cm.run_id = c.run_id
         AND cm.cluster_id = c.cluster_id
        LEFT JOIN stranding_scores ss
          ON ss.run_id = ?
         AND ss.paper_id = cm.paper_id
        WHERE c.run_id = ?
          AND c.level = ?
        GROUP BY c.cluster_id, cluster_label, cluster_summary, c.size
        ORDER BY avg_stranding DESC, max_stranding DESC, c.size DESC, c.cluster_id ASC
        LIMIT ?
        """,
        (stranding_run_id, cluster_run_id, level, limit),
    ).fetchall()
    packets = []
    for row in rows:
        representative_rows = connection.execute(
            """
            SELECT
              p.paper_id,
              COALESCE(p.title, p.paper_id) AS title,
              COALESCE(ss.stranding_score, 0.0) AS stranding_score
            FROM cluster_members cm
            JOIN papers p
              ON p.paper_id = cm.paper_id
            LEFT JOIN stranding_scores ss
              ON ss.run_id = ?
             AND ss.paper_id = cm.paper_id
            WHERE cm.run_id = ?
              AND cm.cluster_id = ?
            ORDER BY stranding_score DESC, title ASC, p.paper_id ASC
            LIMIT 5
            """,
            (stranding_run_id, cluster_run_id, row["cluster_id"]),
        ).fetchall()
        packets.append(
            {
                "packet_kind": "cluster",
                "item_ref": row["cluster_id"],
                "title": f"Cluster packet: {row['cluster_label']}",
                "summary": {
                    "cluster_id": row["cluster_id"],
                    "level": level,
                    "size": int(row["size"]),
                    "avg_stranding": round(float(row["avg_stranding"] or 0.0), 6),
                    "max_stranding": round(float(row["max_stranding"] or 0.0), 6),
                    "representative_papers": [item["paper_id"] for item in representative_rows],
                },
                "markdown": render_cluster_packet(row, representative_rows, level),
                "source_run_ids": {
                    "cluster_run_id": cluster_run_id,
                    "stranding_run_id": stranding_run_id,
                },
            }
        )
    return packets


def render_cluster_packet(row: sqlite3.Row, representative_rows, level: str) -> str:
    lines = [
        f"# Cluster Packet: {row['cluster_label']}",
        "",
        f"- cluster id: `{row['cluster_id']}`",
        f"- level: `{level}`",
        f"- size: `{row['size']}`",
        f"- avg stranding score: `{round(float(row['avg_stranding'] or 0.0), 6)}`",
        f"- max stranding score: `{round(float(row['max_stranding'] or 0.0), 6)}`",
        f"- summary: {row['cluster_summary'] or 'none'}",
        "",
        "## Representative Papers",
    ]
    for item in representative_rows:
        lines.append(f"- `{item['paper_id']}` | {item['title']} | stranding `{round(float(item['stranding_score'] or 0.0), 6)}`")
    return "\n".join(lines) + "\n"


def fetch_pair_packets(connection: sqlite3.Connection, table_name: str, score_column: str, rank_column: str, run_id: str, limit: int, packet_kind: str):
    rows = connection.execute(
        f"""
        SELECT
          source_anchor_id,
          target_anchor_id,
          AVG({score_column}) AS avg_score,
          MAX({score_column}) AS max_score,
          COUNT(*) AS candidate_count
        FROM {table_name}
        WHERE run_id = ?
        GROUP BY source_anchor_id, target_anchor_id
        ORDER BY max_score DESC, avg_score DESC, candidate_count DESC, source_anchor_id ASC, target_anchor_id ASC
        LIMIT ?
        """,
        (run_id, limit),
    ).fetchall()
    packets = []
    for row in rows:
        representative_rows = connection.execute(
            f"""
            SELECT
              c.paper_id,
              COALESCE(p.title, c.paper_id) AS title,
              c.{score_column} AS score
            FROM {table_name} c
            JOIN papers p
              ON p.paper_id = c.paper_id
            WHERE c.run_id = ?
              AND c.source_anchor_id = ?
              AND c.target_anchor_id = ?
            ORDER BY c.{score_column} DESC, c.{rank_column} ASC, p.title ASC, c.paper_id ASC
            LIMIT 5
            """,
            (run_id, row["source_anchor_id"], row["target_anchor_id"]),
        ).fetchall()
        item_ref = f"{row['source_anchor_id']}__{row['target_anchor_id']}"
        packets.append(
            {
                "packet_kind": packet_kind,
                "item_ref": item_ref,
                "title": f"{packet_kind.capitalize()} packet: {row['source_anchor_id']} x {row['target_anchor_id']}",
                "summary": {
                    "source_anchor_id": row["source_anchor_id"],
                    "target_anchor_id": row["target_anchor_id"],
                    "avg_score": round(float(row["avg_score"] or 0.0), 6),
                    "max_score": round(float(row["max_score"] or 0.0), 6),
                    "candidate_count": int(row["candidate_count"]),
                    "representative_papers": [item["paper_id"] for item in representative_rows],
                },
                "markdown": render_pair_packet(packet_kind, row, representative_rows),
                "source_run_ids": {f"{packet_kind}_run_id": run_id},
            }
        )
    return packets


def render_pair_packet(packet_kind: str, row: sqlite3.Row, representative_rows) -> str:
    lines = [
        f"# {packet_kind.capitalize()} Packet: {row['source_anchor_id']} x {row['target_anchor_id']}",
        "",
        f"- source anchor: `{row['source_anchor_id']}`",
        f"- target anchor: `{row['target_anchor_id']}`",
        f"- candidate count: `{row['candidate_count']}`",
        f"- avg score: `{round(float(row['avg_score'] or 0.0), 6)}`",
        f"- max score: `{round(float(row['max_score'] or 0.0), 6)}`",
        "",
        "## Representative Papers",
    ]
    for item in representative_rows:
        lines.append(f"- `{item['paper_id']}` | {item['title']} | score `{round(float(item['score'] or 0.0), 6)}`")
    return "\n".join(lines) + "\n"


def fetch_transition_packets(connection: sqlite3.Connection, run_id: str, limit: int):
    # @context decision -- Transition-state candidates are grouped by pattern rather than anchor pair.
    # Keeping them in review packets lets broadened packet runs expose seam-specific evidence without
    # forcing later shortlist work to infer pattern-level regions back out of paper rows.
    rows = connection.execute(
        """
        SELECT
          pattern_id,
          AVG(transition_state_candidate_score) AS avg_score,
          MAX(transition_state_candidate_score) AS max_score,
          COUNT(*) AS candidate_count
        FROM transition_state_candidates
        WHERE run_id = ?
        GROUP BY pattern_id
        ORDER BY max_score DESC, avg_score DESC, candidate_count DESC, pattern_id ASC
        LIMIT ?
        """,
        (run_id, limit),
    ).fetchall()
    packets = []
    for row in rows:
        representative_rows = connection.execute(
            """
            SELECT
              c.paper_id,
              COALESCE(p.title, c.paper_id) AS title,
              c.transition_state_candidate_score AS score
            FROM transition_state_candidates c
            JOIN papers p
              ON p.paper_id = c.paper_id
            WHERE c.run_id = ?
              AND c.pattern_id = ?
            ORDER BY c.transition_state_candidate_score DESC, c.transition_state_rank ASC, p.title ASC, c.paper_id ASC
            LIMIT 5
            """,
            (run_id, row["pattern_id"]),
        ).fetchall()
        packets.append(
            {
                "packet_kind": "transition_state",
                "item_ref": row["pattern_id"],
                "title": f"Transition-state packet: {row['pattern_id']}",
                "summary": {
                    "pattern_id": row["pattern_id"],
                    "avg_score": round(float(row["avg_score"] or 0.0), 6),
                    "max_score": round(float(row["max_score"] or 0.0), 6),
                    "candidate_count": int(row["candidate_count"]),
                    "representative_papers": [item["paper_id"] for item in representative_rows],
                },
                "markdown": render_transition_packet(row, representative_rows),
                "source_run_ids": {"transition_run_id": run_id},
            }
        )
    return packets


def render_transition_packet(row: sqlite3.Row, representative_rows) -> str:
    lines = [
        f"# Transition-State Packet: {row['pattern_id']}",
        "",
        f"- pattern id: `{row['pattern_id']}`",
        f"- candidate count: `{row['candidate_count']}`",
        f"- avg score: `{round(float(row['avg_score'] or 0.0), 6)}`",
        f"- max score: `{round(float(row['max_score'] or 0.0), 6)}`",
        "",
        "## Representative Papers",
    ]
    for item in representative_rows:
        lines.append(f"- `{item['paper_id']}` | {item['title']} | score `{round(float(item['score'] or 0.0), 6)}`")
    return "\n".join(lines) + "\n"


def fetch_stranded_packets(connection: sqlite3.Connection, stranding_run_id: str, membership_run_id: str, limit: int):
    rows = connection.execute(
        """
        SELECT
          p.paper_id,
          COALESCE(p.title, p.paper_id) AS title,
          COALESCE(p.primary_category, 'unknown') AS primary_category,
          COALESCE(p.published_at, 'unknown') AS published_at,
          ss.stranding_score
        FROM stranding_scores ss
        JOIN corpus_memberships cm
          ON cm.run_id = ?
         AND cm.paper_id = ss.paper_id
         AND cm.corpus_id = 'stranded_alpha'
        JOIN papers p
          ON p.paper_id = ss.paper_id
        WHERE ss.run_id = ?
        ORDER BY ss.stranding_score DESC, title ASC, p.paper_id ASC
        LIMIT ?
        """,
        (membership_run_id, stranding_run_id, limit),
    ).fetchall()
    packets = []
    for row in rows:
        packets.append(
            {
                "packet_kind": "stranded_qfin",
                "item_ref": row["paper_id"],
                "title": f"Stranded q-fin packet: {row['title']}",
                "summary": {
                    "paper_id": row["paper_id"],
                    "primary_category": row["primary_category"],
                    "published_at": row["published_at"],
                    "stranding_score": round(float(row["stranding_score"] or 0.0), 6),
                },
                "markdown": render_stranded_packet(row),
                "source_run_ids": {
                    "stranding_run_id": stranding_run_id,
                    "membership_run_id": membership_run_id,
                },
            }
        )
    return packets


def render_stranded_packet(row: sqlite3.Row) -> str:
    lines = [
        f"# Stranded Q-Fin Packet: {row['title']}",
        "",
        f"- paper id: `{row['paper_id']}`",
        f"- primary category: `{row['primary_category']}`",
        f"- published at: `{row['published_at']}`",
        f"- stranding score: `{round(float(row['stranding_score'] or 0.0), 6)}`",
    ]
    return "\n".join(lines) + "\n"


def persist_packets(connection: sqlite3.Connection, run_id: str, packet_dir: Path, packets: list[dict]) -> dict:
    # @context requirement -- Packet markdown is persisted both on disk and in the canonical store so
    # later stages never have to scrape files or rerun region assembly to recover the reviewed packet.
    connection.execute("DELETE FROM review_packets WHERE run_id = ?", (run_id,))
    counts = {}
    for packet in packets:
        path = write_packet(packet_dir, packet["packet_kind"], packet["item_ref"], packet["markdown"])
        connection.execute(
            """
            INSERT INTO review_packets (
              run_id,
              packet_kind,
              item_ref,
              title,
              packet_path,
              summary_json,
              packet_markdown,
              source_run_ids_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                packet["packet_kind"],
                packet["item_ref"],
                packet["title"],
                str(path),
                json.dumps(packet["summary"], sort_keys=True),
                packet["markdown"],
                json.dumps(packet["source_run_ids"], sort_keys=True),
            ),
        )
        counts[packet["packet_kind"]] = counts.get(packet["packet_kind"], 0) + 1
    return counts


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    packet_dir = output_dir / "review_packets"
    packet_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        log_run_event(
            connection,
            args.run_id,
            "review_packets",
            "started",
            {
                "cluster_run_id": args.cluster_run_id,
                "bridge_run_id": args.bridge_run_id,
                "composition_run_id": args.composition_run_id,
                "transition_run_id": args.transition_run_id,
                "stranding_run_id": args.stranding_run_id,
                "membership_run_id": args.membership_run_id,
            },
        )

        packets = []
        packets.extend(
            fetch_cluster_packets(
                connection,
                args.cluster_run_id,
                args.stranding_run_id,
                args.cluster_level,
                args.top_clusters,
            )
        )
        packets.extend(
            fetch_pair_packets(
                connection,
                "bridge_candidates",
                "bridge_score",
                "bridge_rank",
                args.bridge_run_id,
                args.top_bridges,
                "bridge",
            )
        )
        packets.extend(
            fetch_pair_packets(
                connection,
                "composition_candidates",
                "composition_score",
                "composition_rank",
                args.composition_run_id,
                args.top_compositions,
                "composition",
            )
        )
        packets.extend(fetch_transition_packets(connection, args.transition_run_id, args.top_transitions))
        packets.extend(fetch_stranded_packets(connection, args.stranding_run_id, args.membership_run_id, args.top_stranded))

        counts = persist_packets(connection, args.run_id, packet_dir, packets)
        metrics = {
            "run_id": args.run_id,
            "packet_counts": counts,
            "total_packets": sum(counts.values()),
            "packet_dir": str(packet_dir),
        }
        metrics_path = output_dir / "review_packet_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log_run_event(connection, args.run_id, "review_packets", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
