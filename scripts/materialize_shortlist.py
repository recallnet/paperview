#!/usr/bin/env python3

import argparse
import json
import math
import sqlite3
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised through fixture subprocess without PyYAML
    yaml = None


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "structural-analogy" / "runs"
DEFAULT_RULES_PATH = ROOT / "configs" / "shortlist_rules.yaml"


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize canonical shortlist items from review packets.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--run-id", default="shortlist-materialization-20260328")
    parser.add_argument("--packet-run-id", default="review-packet-materialization-20260328")
    parser.add_argument("--rules-path", default=str(DEFAULT_RULES_PATH))
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def load_yaml(path: Path, default):
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    parsed = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.lower() in {"true", "false"}:
            parsed[key] = value.lower() == "true"
        else:
            try:
                parsed[key] = int(value)
            except ValueError:
                try:
                    parsed[key] = float(value)
                except ValueError:
                    parsed[key] = value
    return parsed or default


def log_run_event(connection: sqlite3.Connection, run_id: str, stage: str, event_type: str, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, stage, event_type, json.dumps(payload, sort_keys=True)),
    )


def packet_priority(packet_kind: str) -> int:
    priorities = {
        "composition": 0,
        "bridge": 1,
        "cluster": 2,
        "stranded_qfin": 3,
    }
    return priorities.get(packet_kind, 99)


def item_type_for_packet(packet_kind: str) -> str:
    if packet_kind == "stranded_qfin":
        return "paper"
    return packet_kind


def packet_score(summary: dict, packet_kind: str) -> float:
    if packet_kind in {"bridge", "composition"}:
        return float(summary.get("max_score") or summary.get("avg_score") or 0.0)
    if packet_kind == "cluster":
        return float(summary.get("avg_stranding") or summary.get("max_stranding") or 0.0)
    if packet_kind == "stranded_qfin":
        return float(summary.get("stranding_score") or 0.0)
    return 0.0


def shortlist_id_for(packet_kind: str, packet_item_ref: str) -> str:
    return f"{packet_kind}:{packet_item_ref}"


def select_rows(rows: list[sqlite3.Row], shortlist_size: int, min_bridge_or_composition_share: float) -> list[sqlite3.Row]:
    # @context decision -- The shortlist must not collapse back to whatever packet kind happens to
    # score highest locally. Enforcing a minimum bridge/composition share preserves the map-first
    # discovery goal by guaranteeing that multi-anchor and bridge logic materially affects selection.
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            -packet_score(json.loads(row["summary_json"]), row["packet_kind"]),
            packet_priority(row["packet_kind"]),
            row["item_ref"],
        ),
    )
    if shortlist_size <= 0:
        return []

    target_bridge_comp = math.ceil(shortlist_size * float(min_bridge_or_composition_share))
    target_bridge_comp = min(target_bridge_comp, sum(1 for row in sorted_rows if row["packet_kind"] in {"bridge", "composition"}))

    selected = []
    selected_keys = set()
    bridge_comp_selected = 0

    for row in sorted_rows:
        if bridge_comp_selected >= target_bridge_comp:
            break
        if row["packet_kind"] not in {"bridge", "composition"}:
            continue
        key = (row["packet_kind"], row["item_ref"])
        if key in selected_keys:
            continue
        selected.append(row)
        selected_keys.add(key)
        bridge_comp_selected += 1

    for row in sorted_rows:
        if len(selected) >= shortlist_size:
            break
        key = (row["packet_kind"], row["item_ref"])
        if key in selected_keys:
            continue
        selected.append(row)
        selected_keys.add(key)

    return selected[:shortlist_size]


def main():
    args = parse_args()
    db_path = Path(args.db_path).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else DEFAULT_OUTPUT_ROOT / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    rules = load_yaml(Path(args.rules_path).resolve(), {"shortlist_size": 12, "minimum_bridge_or_composition_share": 0.2})

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        log_run_event(
            connection,
            args.run_id,
            "shortlist",
            "started",
            {
                "packet_run_id": args.packet_run_id,
                "rules_path": str(Path(args.rules_path).resolve()),
            },
        )
        rows = connection.execute(
            """
            SELECT packet_kind, item_ref, title, summary_json
            FROM review_packets
            WHERE run_id = ?
            ORDER BY packet_kind, item_ref
            """,
            (args.packet_run_id,),
        ).fetchall()
        selected = select_rows(
            rows,
            int(rules.get("shortlist_size", 12)),
            float(rules.get("minimum_bridge_or_composition_share", 0.2)),
        )

        connection.execute("DELETE FROM shortlist_items WHERE run_id = ?", (args.run_id,))

        shortlist_jsonl = []
        counts_by_type = {}
        bridge_comp_count = 0
        for rank, row in enumerate(selected, start=1):
            summary = json.loads(row["summary_json"])
            packet_kind = row["packet_kind"]
            item_type = item_type_for_packet(packet_kind)
            score = packet_score(summary, packet_kind)
            if packet_kind in {"bridge", "composition"}:
                bridge_comp_count += 1
            counts_by_type[item_type] = counts_by_type.get(item_type, 0) + 1
            rationale = {
                "packet_kind": packet_kind,
                "packet_title": row["title"],
                "summary": summary,
                # @context requirement -- Shortlist rationale has to survive beyond markdown packets so
                # later interpretation and analyst review can explain why an item was chosen without
                # recomputing stage-specific ranking logic.
                "selection_reason": "bridge_or_composition_quota" if packet_kind in {"bridge", "composition"} and rank <= bridge_comp_count else "ranked_by_packet_score",
            }
            shortlist_id = shortlist_id_for(packet_kind, row["item_ref"])
            connection.execute(
                """
                INSERT INTO shortlist_items (
                  run_id,
                  shortlist_id,
                  item_type,
                  item_ref,
                  packet_run_id,
                  packet_kind,
                  packet_item_ref,
                  score,
                  shortlist_rank,
                  status,
                  rationale_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?)
                """,
                (
                    args.run_id,
                    shortlist_id,
                    item_type,
                    row["item_ref"],
                    args.packet_run_id,
                    packet_kind,
                    row["item_ref"],
                    score,
                    rank,
                    json.dumps(rationale, sort_keys=True),
                ),
            )
            shortlist_jsonl.append(
                {
                    "shortlist_id": shortlist_id,
                    "item_type": item_type,
                    "item_ref": row["item_ref"],
                    "packet_kind": packet_kind,
                    "score": score,
                    "shortlist_rank": rank,
                    "status": "proposed",
                    "rationale": rationale,
                }
            )

        shortlist_path = output_dir / "shortlist.jsonl"
        with shortlist_path.open("w", encoding="utf-8") as handle:
            for item in shortlist_jsonl:
                handle.write(json.dumps(item, sort_keys=True) + "\n")

        metrics = {
            "run_id": args.run_id,
            "packet_run_id": args.packet_run_id,
            "shortlist_count": len(shortlist_jsonl),
            "counts_by_item_type": counts_by_type,
            "bridge_or_composition_count": bridge_comp_count,
            "minimum_bridge_or_composition_share": float(rules.get("minimum_bridge_or_composition_share", 0.2)),
        }
        metrics_path = output_dir / "shortlist_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log_run_event(connection, args.run_id, "shortlist", "completed", metrics)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
