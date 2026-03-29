import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "paperview_schema.sql"
SCRIPT_PATH = ROOT / "scripts" / "materialize_findings_and_throwaways.py"


def seed_fixture(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.executescript(
        """
        INSERT INTO anchors (anchor_id, label, anchor_type, tags_json) VALUES
          ('auction', 'Auction', 'positive', '[]'),
          ('queue', 'Queue', 'positive', '[]'),
          ('dead_anchor', 'Dead Anchor', 'negative', '[]');

        INSERT INTO agitator_patterns (
          pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active
        ) VALUES
          ('contrast_pattern', 'Contrast Pattern', 'contrast', 'contrast text', '[]', '[]', 1),
          ('near_transition_queue_refill', 'Queue x Refill', 'transition', 'queue refill', '[]', '[]', 1);

        INSERT INTO papers (paper_id, source_corpus, title, primary_category, published_at) VALUES
          ('bridge-paper', 'arxiv', 'Bridge Near Miss Paper', 'q-fin.TR', '2023-01-01'),
          ('composition-paper', 'arxiv', 'Composition Near Miss Paper', 'q-fin.TR', '2023-01-02'),
          ('contrast-paper', 'arxiv', 'Contrast Near Miss Paper', 'q-fin.TR', '2023-01-03'),
          ('negative-paper', 'arxiv', 'Negative Space Paper', 'q-fin.TR', '2023-01-04'),
          ('transition-paper', 'arxiv', 'Transition State Paper', 'q-fin.TR', '2023-01-05'),
          ('paper-fail-a', 'arxiv', 'Failed Stranded Paper A', 'q-fin.PR', '2021-01-01'),
          ('paper-fail-b', 'arxiv', 'Failed Stranded Paper B', 'q-fin.PR', '2022-01-01'),
          ('paper-kept', 'arxiv', 'Kept Stranded Paper', 'q-fin.PR', '2020-01-01');

        INSERT INTO review_packets (
          run_id, packet_kind, item_ref, title, packet_path, summary_json, packet_markdown, source_run_ids_json
        ) VALUES
          ('packet-run', 'bridge', 'bridge-a', 'Bridge Packet A', '/tmp/bridge-a.md', '{}', '# bridge', '{}'),
          ('packet-run', 'composition', 'composition-a', 'Composition Packet A', '/tmp/composition-a.md', '{}', '# comp', '{}'),
          ('packet-run', 'bridge', 'bridge-b', 'Bridge Packet B', '/tmp/bridge-b.md', '{}', '# bridge b', '{}'),
          ('packet-run', 'stranded_qfin', 'paper-fail-a', 'Stranded Packet Fail', '/tmp/paper-fail-a.md', '{}', '# fail', '{}'),
          ('packet-run', 'stranded_qfin', 'paper-kept', 'Stranded Packet Kept', '/tmp/paper-kept.md', '{}', '# kept', '{}');

        INSERT INTO shortlist_items (
          run_id, shortlist_id, item_type, item_ref, packet_run_id, packet_kind, packet_item_ref,
          score, shortlist_rank, status, rationale_json
        ) VALUES
          ('shortlist-run', 'bridge:bridge-a', 'bridge', 'bridge-a', 'packet-run', 'bridge', 'bridge-a', 2.2, 1, 'proposed', '{}'),
          ('shortlist-run', 'composition:composition-a', 'composition', 'composition-a', 'packet-run', 'composition', 'composition-a', 2.0, 2, 'proposed', '{}'),
          ('shortlist-run', 'bridge:bridge-b', 'bridge', 'bridge-b', 'packet-run', 'bridge', 'bridge-b', 1.8, 3, 'proposed', '{}'),
          ('shortlist-run', 'paper:paper-fail-a', 'paper', 'paper-fail-a', 'packet-run', 'stranded_qfin', 'paper-fail-a', 1.4, 4, 'proposed', '{}'),
          ('shortlist-run', 'paper:paper-kept', 'paper', 'paper-kept', 'packet-run', 'stranded_qfin', 'paper-kept', 1.1, 5, 'proposed', '{}'),
          ('shortlist-run', 'stranded_qfin:paper-kept', 'paper', 'paper-kept', 'packet-run', 'stranded_qfin', 'paper-kept', 1.0, 6, 'proposed', '{}');

        INSERT INTO selective_interpretations (
          run_id, shortlist_run_id, shortlist_id, classification, result_summary, first_step,
          instrument_assumed, modern_equivalent, why_stranded_or_unrealized, gap_to_close,
          confidence, raw_json
        ) VALUES
          ('interpret-run', 'shortlist-run', 'bridge:bridge-a', 'TRANSLATION_CANDIDATE', 'bridge result', 'bridge step', 'bridge instrument', 'bridge clue', 'bridge why', 'bridge gap', 'high', '{}'),
          ('interpret-run', 'shortlist-run', 'composition:composition-a', 'COMPOSITIONAL_CANDIDATE', 'composition result', 'composition step', 'composition instrument', 'composition clue', 'composition why', 'composition gap', 'medium', '{}'),
          ('interpret-run', 'shortlist-run', 'paper:paper-fail-a', 'NO_TRANSLATION', 'failed result', 'failed step', 'failed instrument', 'failed clue', 'failed why', 'failed gap', 'medium', '{}'),
          ('interpret-run', 'shortlist-run', 'paper:paper-kept', 'STRANDED_QFIN_RESULT', 'kept result', 'kept step', 'kept instrument', 'kept clue', 'kept why', 'kept gap', 'high', '{}'),
          ('enhanced-run', 'shortlist-run', 'stranded_qfin:paper-kept', 'STRANDED_QFIN_RESULT', 'enhanced kept result', 'enhanced kept step', 'enhanced kept instrument', 'enhanced kept clue', 'enhanced kept why', 'enhanced kept gap', 'high', '{}');

        INSERT INTO enhanced_interpretations (
          run_id, batch_run_id, batch_item_id, operator_family, source_kind, source_run_id, source_ref,
          family_rank, source_score, packet_title, classification, result_summary, first_step,
          instrument_assumed, modern_equivalent, why_stranded_or_unrealized, gap_to_close,
          confidence, raw_json
        ) VALUES
          ('enhanced-run', 'enhanced-batch-run', 'bridge:bridge-a', 'bridge', 'review_packet', 'packet-run', 'bridge-a', 1, 2.2, 'Bridge Packet A', 'TRANSLATION_CANDIDATE', 'enhanced bridge result', 'enhanced bridge step', 'enhanced bridge instrument', 'enhanced bridge clue', 'enhanced bridge why', 'enhanced bridge gap', 'high', '{}'),
          ('enhanced-run', 'enhanced-batch-run', 'bridge:bridge-c', 'bridge', 'review_packet', 'packet-run', 'bridge-c', 2, 1.7, 'Bridge Packet C', 'COMPOSITIONAL_CANDIDATE', 'enhanced bridge comp result', 'enhanced bridge comp step', 'enhanced bridge comp instrument', 'enhanced bridge comp clue', 'enhanced bridge comp why', 'enhanced bridge comp gap', 'medium', '{}'),
          ('enhanced-run', 'enhanced-batch-run', 'stranded_qfin:paper-kept', 'stranded_qfin', 'stranded_resurfacing_candidate', 'resurface-run', 'paper-kept', 1, 0.55, 'Stranded Packet Kept', 'STRANDED_QFIN_RESULT', 'enhanced kept result', 'enhanced kept step', 'enhanced kept instrument', 'enhanced kept clue', 'enhanced kept why', 'enhanced kept gap', 'high', '{}'),
          ('enhanced-run', 'enhanced-batch-run', 'stranded_qfin:paper-fail-a', 'stranded_qfin', 'stranded_resurfacing_candidate', 'resurface-run', 'paper-fail-a', 2, 0.62, 'Stranded Packet Fail', 'NO_TRANSLATION', 'enhanced failed result', 'enhanced failed step', 'enhanced failed instrument', 'enhanced failed clue', 'enhanced failed why', 'enhanced failed gap', 'medium', '{}'),
          ('enhanced-run', 'enhanced-batch-run', 'transition_state:near_transition_queue_refill:transition-paper', 'transition_state', 'transition_state_candidate', 'transition-run', 'near_transition_queue_refill', 1, 0.77, 'Transition-state packet: Queue x Refill', 'TRANSLATION_CANDIDATE', 'enhanced transition result', 'enhanced transition step', 'enhanced transition instrument', 'enhanced transition clue', 'enhanced transition why', 'enhanced transition gap', 'high', '{}');

        INSERT INTO bridge_candidates (
          run_id, source_anchor_id, target_anchor_id, paper_id, bridge_score, bridge_rank, rationale_json
        ) VALUES
          ('bridge-run', 'auction', 'queue', 'bridge-paper', 0.91, 1, '{}');

        INSERT INTO composition_candidates (
          run_id, source_anchor_id, target_anchor_id, paper_id, composition_score, composition_rank, rationale_json
        ) VALUES
          ('composition-run', 'auction', 'queue', 'composition-paper', 0.88, 1, '{}');

        INSERT INTO contrast_candidates (
          run_id, pattern_id, paper_id, contrast_score, contrast_rank, rationale_json
        ) VALUES
          ('contrast-run', 'contrast_pattern', 'contrast-paper', 0.73, 1, '{}');

        INSERT INTO negative_space_candidates (
          run_id, anchor_id, paper_id, negative_space_score, negative_rank, rationale_json
        ) VALUES
          ('negative-run', 'dead_anchor', 'negative-paper', 0.61, 1, '{}');

        INSERT INTO transition_state_candidates (
          run_id, pattern_id, paper_id, transition_state_candidate_score, transition_state_rank, rationale_json
        ) VALUES
          ('transition-run', 'near_transition_queue_refill', 'transition-paper', 0.77, 1, '{}');

        INSERT INTO stranded_resurfacing_candidates (
          run_id, paper_id, resurfacing_score, resurfacing_rank, membership_run_id, stranding_run_id, transition_score_run_id, rationale_json
        ) VALUES
          ('resurface-run', 'paper-fail-a', 0.62, 1, 'membership-run', 'stranding-run', 'transition-run', '{}'),
          ('resurface-run', 'paper-fail-b', 0.58, 2, 'membership-run', 'stranding-run', 'transition-run', '{}'),
          ('resurface-run', 'paper-kept', 0.55, 3, 'membership-run', 'stranding-run', 'transition-run', '{}');

        INSERT INTO stranded_result_ledger (
          run_id, shortlist_run_id, interpretation_run_id, shortlist_id, paper_id, published_at, home_domain,
          result_summary, why_stranded_or_unrealized, instrument_assumed, modern_equivalent, first_test,
          gap_to_close, priority_tier, relation_type, ledger_rank, stranding_score, confidence, rationale_json
        ) VALUES
          ('ledger-run', 'shortlist-run', 'interpret-run', 'paper:paper-kept', 'paper-kept', '2020-01-01', 'q-fin.PR',
           'kept result', 'kept why', 'kept instrument', 'kept clue', 'kept step', 'kept gap', 'p1', 'direct', 1, 0.4, 'high', '{}');

        INSERT INTO stranded_result_ledger (
          run_id, shortlist_run_id, interpretation_run_id, shortlist_id, publication_source_surface, publication_interpretation_run_id, publication_item_id,
          paper_id, published_at, home_domain, result_summary, why_stranded_or_unrealized, instrument_assumed, modern_equivalent, first_test,
          gap_to_close, priority_tier, relation_type, ledger_rank, stranding_score, confidence, rationale_json
        ) VALUES
          ('ledger-enhanced-run', 'shortlist-run', 'enhanced-run', 'stranded_qfin:paper-kept', 'enhanced_interpretation', 'enhanced-run', 'stranded_qfin:paper-kept',
           'paper-kept', '2020-01-01', 'q-fin.PR', 'enhanced kept result', 'enhanced kept why', 'enhanced kept instrument', 'enhanced kept clue', 'enhanced kept step', 'enhanced kept gap', 'p1', 'direct', 1, 0.4, 'high', '{}');
        """
    )
    connection.commit()


class MaterializeFindingsAndThrowawaysTest(unittest.TestCase):
    def test_materializes_findings_report_across_sections(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"
            root_markdown_path = tmp_path / "findings_and_throwaways.md"
            rejections_path = tmp_path / "interpretation_rejections.jsonl"

            connection = sqlite3.connect(db_path)
            seed_fixture(connection)
            connection.close()

            rejections = [
                {"line_number": 1, "shortlist_id": "bridge:bridge-b", "reason": "invalid_enum:classification:BAD_CLASS"},
                {"line_number": 2, "reason": "invalid_json:fixture"},
            ]
            with rejections_path.open("w", encoding="utf-8") as handle:
                for row in rejections:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "findings-run",
                    "--shortlist-run-id",
                    "shortlist-run",
                    "--interpretation-run-id",
                    "interpret-run",
                    "--interpretation-rejections-path",
                    str(rejections_path),
                    "--bridge-run-id",
                    "bridge-run",
                    "--composition-run-id",
                    "composition-run",
                    "--contrast-run-id",
                    "contrast-run",
                    "--negative-space-run-id",
                    "negative-run",
                    "--transition-run-id",
                    "transition-run",
                    "--resurfacing-run-id",
                    "resurface-run",
                    "--stranded-ledger-run-id",
                    "ledger-run",
                    "--output-dir",
                    str(output_dir),
                    "--root-markdown-path",
                    str(root_markdown_path),
                    "--top-k",
                    "3",
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "findings_and_throwaways_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["accepted_count"], 3)
            self.assertEqual(metrics["rejected_count"], 2)
            self.assertEqual(metrics["near_miss_count"], 5)
            self.assertEqual(metrics["stranded_qfin_failure_count"], 2)
            self.assertEqual(metrics["accepted_by_operator"]["bridge"], 1)
            self.assertEqual(metrics["near_miss_by_operator"]["transition_state"], 1)

            rows = [
                json.loads(line)
                for line in (output_dir / "findings_and_throwaways.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            failure_reasons = {
                row["paper_id"]: row["failure_reason"]
                for row in rows
                if row["section"] == "stranded_qfin_failure"
            }
            self.assertEqual(failure_reasons["paper-fail-a"], "interpretation_classification:NO_TRANSLATION")
            self.assertEqual(failure_reasons["paper-fail-b"], "not_shortlisted_for_interpretation")

            markdown = (output_dir / "findings_and_throwaways.md").read_text(encoding="utf-8")
            self.assertIn("# Findings and Throwaways", markdown)
            self.assertIn("## Near Misses By Operator", markdown)
            self.assertIn("Bridge Packet A", markdown)
            self.assertIn("Failed Stranded Paper B", markdown)
            self.assertEqual(root_markdown_path.read_text(encoding="utf-8"), markdown)

    def test_materializes_findings_report_from_enhanced_interpretations(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_path = tmp_path / "fixture.sqlite3"
            output_dir = tmp_path / "run"
            root_markdown_path = tmp_path / "findings_and_throwaways.md"
            rejections_path = tmp_path / "enhanced_interpretation_rejections.jsonl"

            connection = sqlite3.connect(db_path)
            seed_fixture(connection)
            connection.close()

            rejections = [
                {"line_number": 1, "batch_item_id": "bridge:bridge-c", "reason": "invalid_enum:classification:BAD_CLASS"},
                {"line_number": 2, "batch_item_id": "transition_state:near_transition_parity_repair:missing-paper", "reason": "unknown_batch_item_id"},
            ]
            with rejections_path.open("w", encoding="utf-8") as handle:
                for row in rejections:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "findings-enhanced-run",
                    "--shortlist-run-id",
                    "shortlist-run",
                    "--interpretation-source",
                    "enhanced",
                    "--interpretation-run-id",
                    "enhanced-run",
                    "--interpretation-rejections-path",
                    str(rejections_path),
                    "--bridge-run-id",
                    "bridge-run",
                    "--composition-run-id",
                    "composition-run",
                    "--contrast-run-id",
                    "contrast-run",
                    "--negative-space-run-id",
                    "negative-run",
                    "--transition-run-id",
                    "transition-run",
                    "--resurfacing-run-id",
                    "resurface-run",
                    "--stranded-ledger-run-id",
                    "ledger-enhanced-run",
                    "--output-dir",
                    str(output_dir),
                    "--root-markdown-path",
                    str(root_markdown_path),
                    "--top-k",
                    "3",
                ],
                check=True,
                cwd=ROOT,
            )

            metrics = json.loads((output_dir / "findings_and_throwaways_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["interpretation_source"], "enhanced")
            self.assertEqual(metrics["accepted_count"], 4)
            self.assertEqual(metrics["rejected_count"], 2)
            self.assertEqual(metrics["near_miss_count"], 5)
            self.assertEqual(metrics["stranded_qfin_failure_count"], 2)
            self.assertEqual(metrics["accepted_by_operator"]["bridge"], 2)
            self.assertEqual(metrics["accepted_by_operator"]["transition_state"], 1)

            rows = [
                json.loads(line)
                for line in (output_dir / "findings_and_throwaways.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ]
            accepted_ids = {row["shortlist_id"] for row in rows if row["section"] == "accepted"}
            self.assertIn("transition_state:near_transition_queue_refill:transition-paper", accepted_ids)
            self.assertIn("stranded_qfin:paper-kept", accepted_ids)
            rejected_ids = {row["shortlist_id"] for row in rows if row["section"] == "rejected"}
            self.assertIn("bridge:bridge-c", rejected_ids)
            self.assertIn("transition_state:near_transition_parity_repair:missing-paper", rejected_ids)

            failure_reasons = {
                row["paper_id"]: row["failure_reason"]
                for row in rows
                if row["section"] == "stranded_qfin_failure"
            }
            self.assertEqual(failure_reasons["paper-fail-a"], "interpretation_classification:NO_TRANSLATION")
            self.assertEqual(failure_reasons["paper-fail-b"], "not_shortlisted_for_interpretation")

            markdown = (output_dir / "findings_and_throwaways.md").read_text(encoding="utf-8")
            self.assertIn("transition_state:near_transition_queue_refill:transition-paper", markdown)
            self.assertIn("stranded_qfin:paper-kept", markdown)
            self.assertIn("bridge:bridge-c", markdown)
            self.assertIn("Failed Stranded Paper B", markdown)
            self.assertEqual(root_markdown_path.read_text(encoding="utf-8"), markdown)


if __name__ == "__main__":
    unittest.main()
