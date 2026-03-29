import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_ds1_translation_gap.py"


def seed_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(
        """
        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at) VALUES
          ('p-market-design', 'arxiv', 'Market design under refill stress', 'econ.EM', '2023-01-01'),
          ('p-settlement', 'arxiv', 'Async settlement and parity repair', 'cs.GT', '2023-01-02'),
          ('p-queue', 'arxiv', 'Queue-value under refill lag', 'q-fin.TR', '2023-01-03'),
          ('p-stranded', 'arxiv', 'Stranded execution control', 'q-fin.PR', '2022-01-01'),
          ('p-negative', 'arxiv', 'Dead-end negative paper', 'math.PR', '2021-01-01');

        INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source, rationale_json) VALUES
          ('membership-run', 'p-queue', 'realized_market', 'fixture', '{}'),
          ('membership-run', 'p-queue', 'discovery', 'fixture', '{}'),
          ('membership-run', 'p-market-design', 'discovery', 'fixture', '{}'),
          ('membership-run', 'p-settlement', 'discovery', 'fixture', '{}'),
          ('membership-run', 'p-stranded', 'discovery', 'fixture', '{}');

        INSERT INTO text_views (paper_id, view_type, text, token_estimate, text_sha256) VALUES
          ('p-market-design', 'title_abs', 'market design seam', 3, 'a'),
          ('p-settlement', 'title_abs', 'settlement repair', 3, 'b'),
          ('p-queue', 'title_abs', 'queue refill', 3, 'c'),
          ('p-negative', 'title_abs', 'negative', 1, 'd');

        INSERT INTO agitator_patterns (pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active) VALUES
          ('near_market_design_far_realized', 'near market design, far realized-market q-fin', 'contrast', '', '[]', '[]', 1),
          ('near_settlement_resolution_far_realized', 'near settlement and resolution, far realized-market q-fin', 'contrast', '', '[]', '[]', 1),
          ('near_transition_queue_refill', 'near queue value and refill resiliency', 'composition', '', '[]', '[]', 1);

        INSERT INTO anchors (anchor_id, label, anchor_type, tags_json) VALUES
          ('market_design_seams', 'Market-Design Seams', 'positive', '[]'),
          ('participant_pathologies', 'Participant Pathologies', 'positive', '[]'),
          ('amm_settlement_latency', 'AMM Settlement Latency', 'positive', '[]'),
          ('settlement_resolution_seams', 'Settlement / Resolution Seams', 'positive', '[]'),
          ('queue_value_passive_quoting', 'Queue-Value Passive Quoting', 'positive', '[]'),
          ('refill_lag_resiliency', 'Refill-Lag Resiliency', 'positive', '[]'),
          ('dead_anchor', 'Dead Anchor', 'negative', '[]');

        INSERT INTO probe_hits (run_id, pattern_id, view_id, score, rank) VALUES
          ('probe-run', 'near_market_design_far_realized', 1, 0.91, 1),
          ('probe-run', 'near_settlement_resolution_far_realized', 2, 0.88, 1),
          ('probe-run', 'near_transition_queue_refill', 3, 0.95, 1);

        INSERT INTO bridge_candidates (run_id, source_anchor_id, target_anchor_id, paper_id, bridge_score, bridge_rank, rationale_json) VALUES
          ('bridge-run', 'market_design_seams', 'participant_pathologies', 'p-market-design', 2.4, 1, '{}');

        INSERT INTO composition_candidates (run_id, source_anchor_id, target_anchor_id, paper_id, composition_score, composition_rank, rationale_json) VALUES
          ('composition-run', 'amm_settlement_latency', 'settlement_resolution_seams', 'p-settlement', 2.9, 1, '{}'),
          ('composition-run', 'queue_value_passive_quoting', 'refill_lag_resiliency', 'p-queue', 3.0, 1, '{}');

        INSERT INTO transition_state_candidates (run_id, pattern_id, paper_id, transition_state_candidate_score, transition_state_rank, rationale_json) VALUES
          ('transition-run', 'near_transition_queue_refill', 'p-queue', 0.77, 1, '{}');

        INSERT INTO stranded_resurfacing_candidates (run_id, paper_id, resurfacing_score, resurfacing_rank, membership_run_id, stranding_run_id, transition_score_run_id, rationale_json) VALUES
          ('resurfacing-run', 'p-stranded', 0.42, 1, 'membership-run', 'stranding-run', 'transition-run', '{}');

        INSERT INTO negative_space_candidates (run_id, anchor_id, paper_id, negative_space_score, negative_rank, rationale_json) VALUES
          ('negative-run', 'dead_anchor', 'p-negative', 2.8, 1, '{}');
        """
    )
    connection.commit()


class MaterializeDs1TranslationGapTests(unittest.TestCase):
    def test_materializes_translation_gap_reports(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            reports_dir = tmp_path / "reports"
            capsules_path = tmp_path / "challenge_capsules.yaml"

            capsules_path.write_text(
                """
capsules:
  - capsule_id: participant_design_failure
    label: Participant pathology x design
    lane: participant_pathologies
    anchor_ids: [participant_pathologies, market_design_seams]
    pattern_ids: []
    far_realized_patterns: [near_market_design_far_realized]
  - capsule_id: settlement_async_repair
    label: Settlement / async repair
    lane: settlement_resolution
    anchor_ids: [amm_settlement_latency, settlement_resolution_seams]
    pattern_ids: []
    far_realized_patterns: [near_settlement_resolution_far_realized]
  - capsule_id: queue_refill_repair
    label: Queue / refill repair
    lane: transition_state
    anchor_ids: [queue_value_passive_quoting, refill_lag_resiliency]
    pattern_ids: [near_transition_queue_refill]
    far_realized_patterns: []
  - capsule_id: stranded_qfin_rescue
    label: Stranded q-fin rescue
    lane: stranded_qfin
    anchor_ids: []
    pattern_ids: []
    far_realized_patterns: []
                """.strip()
                + "\n",
                encoding="utf-8",
            )

            connection = sqlite3.connect(db_path)
            seed_fixture(connection)
            connection.close()

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--reports-dir",
                    str(reports_dir),
                    "--challenge-capsules-path",
                    str(capsules_path),
                    "--membership-run-id",
                    "membership-run",
                    "--probe-run-id",
                    "probe-run",
                    "--bridge-run-id",
                    "bridge-run",
                    "--composition-run-id",
                    "composition-run",
                    "--transition-run-id",
                    "transition-run",
                    "--resurfacing-run-id",
                    "resurfacing-run",
                    "--negative-space-run-id",
                    "negative-run",
                    "--top-k",
                    "10",
                ],
                check=True,
                cwd=ROOT,
            )

            rows = [
                json.loads(line)
                for line in (reports_dir / "ds1-translation-gap-candidates.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            self.assertGreaterEqual(len(rows), 4)
            top = rows[0]
            self.assertIn("challenge_capsule_matched", top)
            self.assertIn("translation_gap_score", top)
            self.assertIn("why_far_from_realized", top)
            self.assertIn("translation_kind", top)
            self.assertEqual(rows[0]["paper_id"], "p-market-design")
            outside_count = sum(1 for row in rows if row["outside_obvious_qfin_discourse"])
            self.assertGreaterEqual(outside_count, 2)

            report = (reports_dir / "ds1-translation-gap-report.md").read_text(encoding="utf-8")
            self.assertIn("# DS1 Translation-Gap Search", report)
            self.assertIn("## Candidate-Family Diversity", report)
            self.assertIn("participant_design_failure", report)
            self.assertIn("settlement_async_repair", report)


if __name__ == "__main__":
    unittest.main()
