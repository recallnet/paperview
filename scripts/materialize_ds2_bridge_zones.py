#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "structural-analogy" / "paperview.sqlite3"
DEFAULT_REPORTS_DIR = ROOT / "reports"


# @context decision -- DS2 uses fixed bridge-zone definitions from the study brief
# instead of discovering zones opportunistically from the top-scoring pair list.
# That keeps the study comparable across runs and prevents queue/refill from
# reabsorbing the whole report when other cross-lane seams are live.
ZONE_SPECS = [
    {
        "zone_id": "auction_handoff_recovery",
        "label": "Auction / Pari-Mutuel x Refill / Shock-Recovery",
        "distinct_from_queue_refill": True,
        "title_keywords": ["auction", "double auction", "price impact", "liquidity crisis", "order placement"],
        "sources": [
            {
                "table": "bridge_candidates",
                "run_id": "bridge-materialization-20260328-broadened",
                "score_col": "bridge_score",
                "operator_family": "bridge",
                "pairs": [
                    ("auction_parimutuel_design", "refill_lag_local_shock"),
                    ("auction_parimutuel_design", "refill_lag_resiliency"),
                    ("auction_handoff", "refill_lag_local_shock"),
                    ("auction_handoff", "refill_lag_resiliency"),
                ],
            },
            {
                "table": "composition_candidates",
                "run_id": "composition-materialization-20260328-broadened",
                "score_col": "composition_score",
                "operator_family": "composition",
                "pairs": [
                    ("auction_parimutuel_design", "refill_lag_local_shock"),
                    ("auction_parimutuel_design", "refill_lag_resiliency"),
                    ("auction_handoff", "refill_lag_local_shock"),
                    ("auction_handoff", "refill_lag_resiliency"),
                ],
            },
        ],
        "why_neither_side_alone": "Auction and pari-mutuel papers explain uncrossing and batch clearing, while refill and shock-recovery papers explain post-event book healing. Neither side alone tells you whether uncrossing conditions create a temporary quoting seam as the continuous book repopulates.",
        "translation_questions": [
            "Does queue priority gained in the first post-uncrossing window price adverse selection differently than queue priority gained later in continuous trading?",
            "Which auction imbalance or clearing-price features predict slow versus fast depth refill after the switch back to continuous matching?",
            "Are post-auction liquidity crises best modeled as auction design failures, resiliency failures, or an interaction between the two?",
        ],
    },
    {
        "zone_id": "settlement_parity_repair",
        "label": "Settlement / Async-Repair x Parity / Consistency",
        "distinct_from_queue_refill": True,
        "title_keywords": ["arbitrage", "liquidity provider", "defi", "counterparty", "otc", "derivatives", "credit"],
        "sources": [
            {
                "table": "bridge_candidates",
                "run_id": "bridge-materialization-20260328-broadened",
                "score_col": "bridge_score",
                "operator_family": "bridge",
                "pairs": [
                    ("amm_settlement_latency", "parity_propagation_delayed_repair"),
                    ("settlement_resolution_seams", "parity_propagation_delayed_repair"),
                    ("amm_settlement_latency", "state_graph_inconsistencies"),
                    ("settlement_resolution_seams", "state_graph_inconsistencies"),
                ],
            },
            {
                "table": "composition_candidates",
                "run_id": "composition-materialization-20260328-broadened",
                "score_col": "composition_score",
                "operator_family": "composition",
                "pairs": [
                    ("amm_settlement_latency", "parity_propagation_delayed_repair"),
                    ("settlement_resolution_seams", "parity_propagation_delayed_repair"),
                    ("amm_settlement_latency", "state_graph_inconsistencies"),
                    ("settlement_resolution_seams", "state_graph_inconsistencies"),
                ],
            },
        ],
        "why_neither_side_alone": "Settlement and resolution papers explain delayed finality, collateral, and close-out mechanics, while parity and consistency papers explain when linked markets disagree. The bridge matters because asynchronous settlement is often the reason the inconsistency persists long enough to trade.",
        "translation_questions": [
            "Which settlement frictions turn a nominal parity deviation into a durable, harvestable repair trade rather than a transient quote mismatch?",
            "Do CCP, collateral, or AMM liquidation rules explain why some cross-market inconsistencies remain open longer than others?",
            "Can parity-repair opportunities be ranked by the time it takes collateral or counterparty state to synchronize?",
        ],
    },
    {
        "zone_id": "participant_design_pathologies",
        "label": "Participant-Pathology x Market-Design",
        "distinct_from_queue_refill": True,
        "title_keywords": ["manipulation", "hft", "latency", "informed", "market impact", "synchronizing", "order imbalance"],
        "sources": [
            {
                "table": "bridge_candidates",
                "run_id": "bridge-materialization-20260328-broadened",
                "score_col": "bridge_score",
                "operator_family": "bridge",
                "pairs": [
                    ("market_design_seams", "participant_pathologies"),
                    ("auction_handoff", "participant_pathologies"),
                ],
            },
            {
                "table": "composition_candidates",
                "run_id": "composition-materialization-20260328-broadened",
                "score_col": "composition_score",
                "operator_family": "composition",
                "pairs": [
                    ("market_design_seams", "participant_pathologies"),
                    ("auction_handoff", "participant_pathologies"),
                ],
            },
        ],
        "why_neither_side_alone": "Participant-pathology papers explain who behaves badly or predictably, and market-design papers explain which rules shape order handling. The bridge is the operational question: which rules amplify or suppress predictable bad behavior enough to create repeatable edge?",
        "translation_questions": [
            "Which venue rules make informed, latency-sensitive, or manipulative flow most visible to passive or reactive strategies?",
            "Do tick-size, priority, or auction rules change the persistence of participant-driven imbalance signals?",
            "Which participant pathologies become tradeable only after they interact with a specific market-design seam?",
        ],
    },
    {
        "zone_id": "queue_service_discipline",
        "label": "Queue-Value x Overloaded / Service-Discipline",
        "distinct_from_queue_refill": True,
        "title_keywords": ["market making", "latency", "order flow", "matching engine", "liquidity provision", "market maker"],
        "sources": [
            {
                "table": "bridge_candidates",
                "run_id": "bridge-materialization-20260328-broadened",
                "score_col": "bridge_score",
                "operator_family": "bridge",
                "pairs": [
                    ("queue_value_passive_quoting", "participant_pathologies"),
                    ("queue_value_passive_quoting", "market_design_seams"),
                    ("queue_value_passive_quoting", "lifecycle_professionalization"),
                ],
            },
            {
                "table": "composition_candidates",
                "run_id": "composition-materialization-20260328-broadened",
                "score_col": "composition_score",
                "operator_family": "composition",
                "pairs": [
                    ("queue_value_passive_quoting", "participant_pathologies"),
                    ("queue_value_passive_quoting", "market_design_seams"),
                    ("queue_value_passive_quoting", "lifecycle_professionalization"),
                ],
            },
        ],
        "why_neither_side_alone": "Queue-value papers explain why position in line matters, but they usually assume a stable service discipline. Lifecycle, design, and participant-load papers explain when the matching engine, participant mix, or latency regime changes the effective service discipline itself.",
        "translation_questions": [
            "When does queue position stop approximating time priority because the venue is effectively overloaded or dominated by faster actors?",
            "Which market-making signals survive when service discipline is distorted by latency, batching, or concentrated participant load?",
            "Can queue-value be conditioned on venue maturity or overload proxies without collapsing back to naive spread-based quoting?",
        ],
    },
    {
        "zone_id": "defi_immature_repair",
        "label": "DeFi / Bridge / Liquidation x Immature-Market Repair",
        "distinct_from_queue_refill": True,
        "title_keywords": ["defi", "decentralized", "amm", "uniswap", "blockchain", "liquidation", "bridge"],
        "sources": [
            {
                "table": "bridge_candidates",
                "run_id": "bridge-materialization-20260328-broadened",
                "score_col": "bridge_score",
                "operator_family": "bridge",
                "pairs": [
                    ("amm_settlement_latency", "settlement_resolution_seams"),
                    ("lifecycle_professionalization", "market_design_seams"),
                    ("lifecycle_professionalization", "participant_pathologies"),
                ],
            },
            {
                "table": "composition_candidates",
                "run_id": "composition-materialization-20260328-broadened",
                "score_col": "composition_score",
                "operator_family": "composition",
                "pairs": [
                    ("amm_settlement_latency", "settlement_resolution_seams"),
                    ("lifecycle_professionalization", "market_design_seams"),
                    ("lifecycle_professionalization", "participant_pathologies"),
                ],
            },
        ],
        "why_neither_side_alone": "DeFi, bridge, and liquidation papers explain immature-market plumbing, while lifecycle and repair papers explain how young markets eventually harden. The seam is in markets that are still too thin or underspecified for arbitrage to close the failure mode immediately.",
        "translation_questions": [
            "Which DeFi liquidation or bridge failures are really immature-market repair problems rather than purely smart-contract problems?",
            "What closes these seams first in practice: professionalized liquidity, rule changes, faster settlement, or cross-venue competition?",
            "Which repair dynamics from early electronic markets transfer cleanly into current thin on-chain venues?",
        ],
    },
]


def parse_args():
    parser = argparse.ArgumentParser(description="Materialize DS2 bridge-zone mining outputs.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def normalized_score(operator_family: str, raw_score: float) -> float:
    if operator_family == "bridge":
        return min(1.5, raw_score / 2.7)
    return min(1.8, raw_score / 3.5)


def keyword_hits(title: str, keywords: list[str]) -> int:
    lowered = title.lower()
    return sum(1 for keyword in keywords if keyword in lowered)


def fetch_zone_rows(connection: sqlite3.Connection, zone: dict, top_k: int) -> list[dict]:
    aggregated: dict[str, dict] = {}
    for source in zone["sources"]:
        pair_clauses = []
        params: list[str] = [source["run_id"]]
        for anchor_a, anchor_b in source["pairs"]:
            pair_clauses.append("((candidate.source_anchor_id = ? AND candidate.target_anchor_id = ?) OR (candidate.source_anchor_id = ? AND candidate.target_anchor_id = ?))")
            params.extend([anchor_a, anchor_b, anchor_b, anchor_a])
        query = f"""
            SELECT
              candidate.paper_id,
              candidate.source_anchor_id,
              candidate.target_anchor_id,
              candidate.{source["score_col"]} AS raw_score,
              paper.title,
              paper.primary_category,
              paper.published_at
            FROM {source["table"]} candidate
            JOIN papers paper
              ON paper.paper_id = candidate.paper_id
            WHERE candidate.run_id = ?
              AND ({' OR '.join(pair_clauses)})
        """
        for row in connection.execute(query, params).fetchall():
            paper_id = row["paper_id"]
            hit_count = keyword_hits(row["title"], zone["title_keywords"])
            candidate = {
                "paper_id": paper_id,
                "title": row["title"],
                "primary_category": row["primary_category"],
                "published_at": row["published_at"],
                "source_operator_family": source["operator_family"],
                "source_anchor_id": row["source_anchor_id"],
                "target_anchor_id": row["target_anchor_id"],
                "score": round(float(row["raw_score"]), 6),
                "normalized_score": round(normalized_score(source["operator_family"], float(row["raw_score"])), 6),
                "title_keyword_hits": hit_count,
            }
            existing = aggregated.get(paper_id)
            if existing is None or (candidate["title_keyword_hits"], candidate["normalized_score"], candidate["score"]) > (
                existing["title_keyword_hits"],
                existing["normalized_score"],
                existing["score"],
            ):
                aggregated[paper_id] = candidate
    ranked = sorted(
        aggregated.values(),
        key=lambda item: (
            -item["title_keyword_hits"],
            -item["normalized_score"],
            -item["score"],
            item["paper_id"],
        ),
    )
    return ranked[:top_k]


def bridge_thesis(zone: dict, top_papers: list[dict]) -> str:
    cited = ", ".join(f"{paper['paper_id']} ({paper['title']})" for paper in top_papers[:3])
    if zone["zone_id"] == "auction_handoff_recovery":
        return f"This bridge zone points to a post-uncrossing repair seam: auction and pari-mutuel papers appear alongside liquidity-shock and refill studies, suggesting that auction clearing conditions shape the first continuous-book refill regime. The strongest supporting papers currently include {cited}, which together imply that the exploitable edge is not auction pricing alone or refill alone, but the handoff between them."
    if zone["zone_id"] == "settlement_parity_repair":
        return f"This zone connects asynchronous settlement and collateral mechanics to parity and consistency failures across linked markets. The supporting papers {cited} suggest that delayed repair is often a settlement-state problem, which means the edge comes from knowing when consistency cannot be restored immediately even if the mispricing is obvious."
    if zone["zone_id"] == "participant_design_pathologies":
        return f"This bridge zone says participant behavior becomes more predictable when market rules expose or amplify it. The supporting papers {cited} frame the opportunity as a rule-behavior interaction problem: design choices around priority, latency, or auctions determine whether toxic or manipulative flow leaves repeatable signatures."
    if zone["zone_id"] == "queue_service_discipline":
        return f"This zone broadens queue value beyond normal-book microstructure by tying it to changing service discipline under automation, participant load, and venue evolution. The papers {cited} imply that queue value is only dependable when the effective matching discipline is understood, especially in markets where overload, latency, or professionalization shift who actually gets served first."
    return f"This bridge zone ties immature-market repair problems to DeFi and other thin venues where rules, settlement, and liquidity are still co-evolving. The strongest supporting papers {cited} suggest that some on-chain edges are really early-market repair seams that persist because the market is not yet professionalized enough to close them quickly."


def render_report(rows: list[dict], metrics: dict) -> str:
    lines = [
        "# DS2 Bridge-Zone Mining",
        "",
        "This study forces bridge families that should matter for diamond hunting in early, weakly arbitraged, or structurally immature markets.",
        "",
        "## Stop / Go",
        "",
        f"- bridge zones materialized: `{metrics['zone_count']}`",
        f"- non-empty bridge zones beyond queue/refill: `{metrics['distinct_zone_count']}`",
        f"- success threshold met: `{str(metrics['success']).lower()}`",
        "",
        "## Candidate-Family Diversity",
        "",
    ]
    for zone_id, count in metrics["papers_per_zone"].items():
        lines.append(f"- {zone_id}: `{count}`")
    for zone in rows:
        lines.extend(
            [
                "",
                f"## {zone['label']}",
                "",
                zone["bridge_thesis"],
                "",
                f"Why neither side alone gives the full idea: {zone['why_neither_side_alone']}",
                "",
                "Translation questions:",
            ]
        )
        for question in zone["candidate_translation_questions"]:
            lines.append(f"- {question}")
        lines.extend(["", "Top papers:"])
        for paper in zone["top_papers"]:
            lines.append(
                f"- `{paper['paper_id']}` | `{paper['source_operator_family']}` | `{paper['source_anchor_id']} x {paper['target_anchor_id']}` | {paper['title']}"
            )
    return "\n".join(lines).rstrip() + "\n"


def log_run_event(connection: sqlite3.Connection, payload: dict) -> None:
    connection.execute(
        """
        INSERT INTO run_events (run_id, stage, event_type, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        ("ds2-bridge-zone-mining", "diamond_study", "completed", json.dumps(payload, sort_keys=True)),
    )


def main() -> None:
    args = parse_args()
    reports_dir = Path(args.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(Path(args.db_path).resolve()))
    connection.row_factory = sqlite3.Row
    try:
        rows = []
        for zone in ZONE_SPECS:
            top_papers = fetch_zone_rows(connection, zone, args.top_k)
            rows.append(
                {
                    "zone_id": zone["zone_id"],
                    "label": zone["label"],
                    "distinct_from_queue_refill": zone["distinct_from_queue_refill"],
                    "bridge_thesis": bridge_thesis(zone, top_papers),
                    "why_neither_side_alone": zone["why_neither_side_alone"],
                    "candidate_translation_questions": zone["translation_questions"],
                    "top_papers": top_papers,
                }
            )
        metrics = {
            "zone_count": len(rows),
            "distinct_zone_count": sum(
                1 for row in rows if row["distinct_from_queue_refill"] and row["top_papers"]
            ),
            "papers_per_zone": {row["zone_id"]: len(row["top_papers"]) for row in rows},
        }
        metrics["success"] = metrics["distinct_zone_count"] >= 5

        jsonl_path = reports_dir / "ds2-bridge-zones.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        markdown_path = reports_dir / "ds2-bridge-zones-report.md"
        markdown_path.write_text(render_report(rows, metrics), encoding="utf-8")

        log_run_event(
            connection,
            {
                "zone_count": metrics["zone_count"],
                "distinct_zone_count": metrics["distinct_zone_count"],
                "success": metrics["success"],
                "reports_dir": str(reports_dir),
            },
        )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
