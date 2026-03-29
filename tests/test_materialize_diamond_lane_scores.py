import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_diamond_lane_scores.py"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def seed_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(
        """
        INSERT INTO anchors (anchor_id, label, anchor_type, tags_json) VALUES
          ('auction_handoff', 'Auction handoff', 'positive', '[]'),
          ('market_design_seams', 'Market-design seams', 'positive', '[]'),
          ('participant_pathologies', 'Participant pathologies', 'positive', '[]'),
          ('settlement_resolution_seams', 'Settlement / resolution seams', 'positive', '[]'),
          ('state_graph_inconsistencies', 'State-graph inconsistencies', 'positive', '[]');

        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at) VALUES
          ('p-transition', 'arxiv', 'Auction refill asymmetry', 'q-fin.ST', '2021-01-01'),
          ('p-market', 'arxiv', 'Venue rules and dark queue priority', 'econ.GN', '2021-01-02'),
          ('p-settlement', 'arxiv', 'Settlement repair and delayed parity', 'cs.GT', '2021-01-03'),
          ('p-stranded', 'arxiv', 'Impact-aware execution control', 'q-fin.TR', '2021-01-04'),
          ('p-outside', 'arxiv', 'Outside holdout paper', 'q-fin.TR', '2024-01-01');

        INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source) VALUES
          ('membership-run', 'p-transition', 'discovery', 'fixture'),
          ('membership-run', 'p-market', 'discovery', 'fixture'),
          ('membership-run', 'p-settlement', 'discovery', 'fixture'),
          ('membership-run', 'p-stranded', 'discovery', 'fixture');

        INSERT INTO text_views (view_id, paper_id, view_type, text, token_estimate, text_sha256) VALUES
          (1, 'p-transition', 'title_abs', 'auction refill asymmetry', 3, 'a'),
          (2, 'p-market', 'title_abs', 'venue rules and dark queue priority', 4, 'b'),
          (3, 'p-settlement', 'title_abs', 'settlement repair and delayed parity', 4, 'c'),
          (4, 'p-stranded', 'title_abs', 'impact-aware execution control', 3, 'd'),
          (5, 'p-outside', 'title_abs', 'outside holdout paper', 3, 'e');

        INSERT INTO agitator_patterns (pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active) VALUES
          ('near_transition_auction_queue', 'auction queue', 'composition', '', '[]', '[]', 1),
          ('near_market_design_far_realized', 'market design far realized', 'contrast', '', '[]', '[]', 1),
          ('near_settlement_resolution_far_realized', 'settlement far realized', 'contrast', '', '[]', '[]', 1),
          ('near_lifecycle_far_realized', 'lifecycle far realized', 'contrast', '', '[]', '[]', 1);

        INSERT INTO probe_hits (run_id, pattern_id, view_id, score, rank) VALUES
          ('probe-run', 'near_transition_auction_queue', 1, 1.2, 1),
          ('probe-run', 'near_market_design_far_realized', 2, 1.4, 1),
          ('probe-run', 'near_settlement_resolution_far_realized', 3, 1.5, 1),
          ('probe-run', 'near_lifecycle_far_realized', 2, 1.1, 1),
          ('probe-run', 'near_market_design_far_realized', 5, 1.6, 1);

        INSERT INTO bridge_candidates (run_id, source_anchor_id, target_anchor_id, paper_id, bridge_score, bridge_rank, rationale_json) VALUES
          ('bridge-run', 'market_design_seams', 'participant_pathologies', 'p-market', 2.7, 1, '{}');

        INSERT INTO composition_candidates (run_id, source_anchor_id, target_anchor_id, paper_id, composition_score, composition_rank, rationale_json) VALUES
          ('composition-run', 'settlement_resolution_seams', 'state_graph_inconsistencies', 'p-settlement', 3.1, 1, '{}');

        INSERT INTO transition_state_scores (
          run_id, paper_id, membership_run_id, probe_run_id, score_version, transition_state_score,
          queue_value_score, refill_resiliency_score, auction_handoff_score, maker_retreat_score,
          parity_repair_score, sparse_component_score, proximity_component_score, family_count, feature_json
        ) VALUES
          ('transition-score-run', 'p-transition', 'membership-run', 'probe-run', 'fixture', 0.82, 0.4, 0.3, 0.8, 0.0, 0.0, 0.2, 0.7, 3, '{}');

        INSERT INTO stranded_resurfacing_candidates (
          run_id, paper_id, resurfacing_score, resurfacing_rank, membership_run_id, stranding_run_id, transition_score_run_id, rationale_json
        ) VALUES
          ('stranded-run', 'p-stranded', 0.41, 1, 'membership-run', 'stranding-run', 'transition-score-run', '{}');
        """
    )
    connection.commit()


class MaterializeDiamondLaneScoresTests(unittest.TestCase):
    def test_materializes_canonical_six_lane_scores(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            reports_dir = tmp_path / "reports"
            reports_dir.mkdir()

            connection = sqlite3.connect(db_path)
            seed_fixture(connection)
            connection.close()

            capsules_path = tmp_path / "challenge_capsules.yaml"
            capsules_path.write_text(
                """
capsules:
  - capsule_id: auction_handoff_repair
    lane: transition_state
    anchor_ids: [auction_handoff]
    pattern_ids: [near_transition_auction_queue]
    far_realized_patterns: []
  - capsule_id: participant_design_failure
    lane: participant_pathologies
    anchor_ids: [market_design_seams, participant_pathologies]
    pattern_ids: []
    far_realized_patterns: [near_market_design_far_realized]
  - capsule_id: settlement_async_repair
    lane: settlement_resolution
    anchor_ids: [settlement_resolution_seams, state_graph_inconsistencies]
    pattern_ids: []
    far_realized_patterns: [near_settlement_resolution_far_realized]
  - capsule_id: state_graph_repair
    lane: state_graph
    anchor_ids: [state_graph_inconsistencies]
    pattern_ids: []
    far_realized_patterns: []
  - capsule_id: thin_market_professionalization
    lane: lifecycle
    anchor_ids: [lifecycle_professionalization, market_design_seams]
    pattern_ids: []
    far_realized_patterns: [near_lifecycle_far_realized]
  - capsule_id: stranded_qfin_rescue
    lane: stranded_qfin
    anchor_ids: []
    pattern_ids: []
    far_realized_patterns: []
""".strip(),
                encoding="utf-8",
            )

            write_jsonl(
                reports_dir / "ds1-translation-gap-candidates.jsonl",
                [
                    {
                        "paper_id": "p-market",
                        "challenge_capsule_matched": "participant_design_failure",
                        "translation_gap_score": 6.3,
                        "outside_obvious_qfin_discourse": True,
                        "translation_kind": "compositional",
                    },
                    {
                        "paper_id": "p-settlement",
                        "challenge_capsule_matched": "settlement_async_repair",
                        "translation_gap_score": 5.8,
                        "outside_obvious_qfin_discourse": True,
                        "translation_kind": "direct",
                    },
                    {
                        "paper_id": "p-market",
                        "challenge_capsule_matched": "thin_market_professionalization",
                        "translation_gap_score": 4.0,
                        "outside_obvious_qfin_discourse": True,
                        "translation_kind": "speculative",
                    },
                ],
            )
            write_jsonl(
                reports_dir / "ds3-early-market-ledger.jsonl",
                [
                    {"paper_id": "p-market", "lane_family": "market_design", "early_market_score": 4.7, "rank": 1},
                    {"paper_id": "p-settlement", "lane_family": "state_graph", "early_market_score": 4.8, "rank": 2},
                    {"paper_id": "p-market", "lane_family": "lifecycle", "early_market_score": 4.6, "rank": 3},
                ],
            )
            write_jsonl(
                reports_dir / "ds4-stranded-ledger.jsonl",
                [
                    {
                        "paper_id": "p-stranded",
                        "resurfacing_score": 0.41,
                        "rescue_family": "execution_control",
                        "executable_research_task": True,
                    }
                ],
            )
            write_jsonl(
                reports_dir / "ds5-holdout-echo-report.jsonl",
                [
                    {
                        "candidate_paper_id": "p-settlement",
                        "candidate_family": "state_graph",
                        "top_echo_score": 0.79,
                        "echo_verdict": "validation",
                    }
                ],
            )

            output_dir = tmp_path / "lane-run"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "lane-run",
                    "--membership-run-id",
                    "membership-run",
                    "--probe-run-id",
                    "probe-run",
                    "--bridge-run-id",
                    "bridge-run",
                    "--composition-run-id",
                    "composition-run",
                    "--transition-score-run-id",
                    "transition-score-run",
                    "--stranded-run-id",
                    "stranded-run",
                    "--challenge-capsules-path",
                    str(capsules_path),
                    "--reports-dir",
                    str(reports_dir),
                    "--output-dir",
                    str(output_dir),
                    "--top-k",
                    "4",
                ],
                check=True,
                cwd=ROOT,
            )

            connection = sqlite3.connect(db_path)
            try:
                rows = connection.execute(
                    """
                    SELECT paper_id, transition_state_score, market_design_score, settlement_resolution_score,
                           participant_pathologies_score, state_graph_score, stranded_qfin_score,
                           lifecycle_aux_score, top_lane
                    FROM diamond_lane_scores
                    WHERE run_id='lane-run'
                    ORDER BY paper_id
                    """
                ).fetchall()
            finally:
                connection.close()

            self.assertEqual(len(rows), 4)
            by_paper = {row[0]: row for row in rows}
            self.assertEqual(by_paper["p-transition"][8], "transition_state")
            self.assertGreater(by_paper["p-transition"][1], 0.45)
            self.assertIn(by_paper["p-market"][8], {"market_design", "participant_pathologies"})
            self.assertGreater(by_paper["p-market"][2], 0.0)
            self.assertGreater(by_paper["p-market"][4], 0.0)
            self.assertGreater(by_paper["p-market"][7], 0.0)
            self.assertIn(by_paper["p-settlement"][8], {"state_graph", "settlement_resolution"})
            self.assertGreater(by_paper["p-settlement"][3], 0.0)
            self.assertGreater(by_paper["p-settlement"][5], 0.0)
            self.assertEqual(by_paper["p-stranded"][8], "stranded_qfin")
            self.assertGreater(by_paper["p-stranded"][6], 0.6)

            metrics = json.loads((output_dir / "diamond_lane_score_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["scored_papers"], 4)
            self.assertGreaterEqual(metrics["top_20_lane_diversity"], 3)
            self.assertIn("market_design", metrics["positive_score_papers_by_lane"])


if __name__ == "__main__":
    unittest.main()
