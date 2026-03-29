import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MaterializeTransitionStateScoresTests(unittest.TestCase):
    def test_transition_state_score_stage_writes_continuous_scores(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            canonical_db = tmp / "paperview.sqlite3"
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "init_local_store.py"), "--db-path", str(canonical_db)],
                check=True,
                cwd=ROOT,
            )
            conn = sqlite3.connect(str(canonical_db))
            conn.executescript(
                """
                INSERT INTO papers (paper_id, source_corpus, title, abstract) VALUES
                  ('p1', 'arxiv', 'queue refill signal', 'queue value and refill lag after local shock'),
                  ('p2', 'arxiv', 'auction handoff note', 'opening auction handoff with reopening friction'),
                  ('p3', 'arxiv', 'dead end', 'pure theorem note');
                INSERT INTO text_views (view_id, paper_id, view_type, text, token_estimate, text_sha256) VALUES
                  (1, 'p1', 'title_abs', 'queue refill signal', 3, 'a'),
                  (2, 'p2', 'title_abs', 'auction handoff note', 3, 'b'),
                  (3, 'p3', 'title_abs', 'dead end', 2, 'c');
                INSERT INTO corpus_memberships (run_id, paper_id, corpus_id, membership_source) VALUES
                  ('membership-run', 'p1', 'discovery', 'fixture'),
                  ('membership-run', 'p2', 'discovery', 'fixture'),
                  ('membership-run', 'p3', 'discovery', 'fixture');
                INSERT INTO agitator_patterns (pattern_id, label, kind, text, positive_tags_json, negative_tags_json, active) VALUES
                  ('near_transition_queue_refill', 'queue refill', 'composition', '', '[]', '[]', 1),
                  ('near_transition_auction_refill', 'auction refill', 'composition', '', '[]', '[]', 1),
                  ('near_transition_auction_queue', 'auction queue', 'composition', '', '[]', '[]', 1),
                  ('near_transition_maker_queue', 'maker queue', 'composition', '', '[]', '[]', 1),
                  ('near_transition_parity_repair', 'parity repair', 'composition', '', '[]', '[]', 1);
                INSERT INTO probe_hits (run_id, pattern_id, view_id, score, rank) VALUES
                  ('probe-run', 'near_transition_queue_refill', 1, 2.0, 1),
                  ('probe-run', 'near_transition_auction_queue', 2, 1.0, 1);
                """
            )
            conn.commit()
            conn.close()

            anchors = tmp / "anchors.yaml"
            anchors.write_text(
                """
anchors:
  - anchor_id: queue_value_passive_quoting
    label: Queue
    anchor_type: positive
    keywords: [queue value, queue]
    min_keyword_hits: 1
    tags: [transition-state]
  - anchor_id: refill_lag_resiliency
    label: Refill
    anchor_type: positive
    keywords: [refill lag, local shock]
    min_keyword_hits: 1
    tags: [transition-state]
  - anchor_id: auction_handoff
    label: Auction
    anchor_type: positive
    keywords: [auction handoff, reopening]
    min_keyword_hits: 1
    tags: [transition-state]
  - anchor_id: maker_retreat_inventory_stress
    label: Maker
    anchor_type: positive
    keywords: [maker retreat, inventory stress]
    min_keyword_hits: 1
    tags: [transition-state]
  - anchor_id: parity_propagation_delayed_repair
    label: Parity
    anchor_type: positive
    keywords: [parity propagation, delayed repair]
    min_keyword_hits: 1
    tags: [transition-state]
""".strip(),
                encoding="utf-8",
            )
            probes = tmp / "probes.yaml"
            probes.write_text(
                """
patterns:
  - pattern_id: near_transition_queue_refill
    label: queue refill
    kind: composition
    include: [queue_value_passive_quoting, refill_lag_resiliency]
  - pattern_id: near_transition_auction_refill
    label: auction refill
    kind: composition
    include: [auction_handoff, refill_lag_resiliency]
  - pattern_id: near_transition_auction_queue
    label: auction queue
    kind: composition
    include: [auction_handoff, queue_value_passive_quoting]
  - pattern_id: near_transition_maker_queue
    label: maker queue
    kind: composition
    include: [maker_retreat_inventory_stress, queue_value_passive_quoting]
  - pattern_id: near_transition_parity_repair
    label: parity repair
    kind: composition
    include: [parity_propagation_delayed_repair, refill_lag_resiliency]
""".strip(),
                encoding="utf-8",
            )
            output_dir = tmp / "transition-score-run"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "materialize_transition_state_scores.py"),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "transition-score-run",
                    "--membership-run-id",
                    "membership-run",
                    "--probe-run-id",
                    "probe-run",
                    "--anchors-path",
                    str(anchors),
                    "--probes-path",
                    str(probes),
                    "--output-dir",
                    str(output_dir),
                    "--top-k",
                    "2",
                ],
                check=True,
                cwd=ROOT,
            )

            conn = sqlite3.connect(str(canonical_db))
            try:
                rows = conn.execute(
                    """
                    SELECT paper_id, transition_state_score, queue_value_score, refill_resiliency_score,
                           auction_handoff_score, family_count
                    FROM transition_state_scores
                    WHERE run_id='transition-score-run'
                    ORDER BY paper_id
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(len(rows), 3)
            by_paper = {row[0]: row for row in rows}
            self.assertGreater(by_paper["p1"][1], by_paper["p2"][1])
            self.assertGreater(by_paper["p2"][1], 0.0)
            self.assertLess(by_paper["p2"][1], 1.0)
            self.assertEqual(by_paper["p3"][1], 0.0)
            self.assertGreater(by_paper["p1"][2], 0.0)
            self.assertGreater(by_paper["p1"][3], 0.0)
            self.assertGreaterEqual(by_paper["p1"][5], 2)

            metrics = json.loads((output_dir / "transition_state_score_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["scored_papers"], 3)
            self.assertEqual(metrics["positive_score_papers"], 2)


if __name__ == "__main__":
    unittest.main()
