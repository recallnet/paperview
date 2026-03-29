import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sqlite_vec_adapter import connect as connect_vec_store, ensure_vec_table, write_vectors
from materialize_probes import prepare_space_payloads


class MaterializeProbesTests(unittest.TestCase):
    def test_prepare_space_payloads_loads_each_space_once(self):
        conn = sqlite3.connect(":memory:")
        try:
            embedding_metrics = {
                "spaces": [
                    {"name": "space_one", "dims": 4, "view_type": "title_abs", "table_name": "vec_space_one_4"},
                    {"name": "space_two", "dims": 4, "view_type": "title_abs", "table_name": "vec_space_two_4"},
                ]
            }
            with patch("materialize_probes.load_space_vectors") as load_space_vectors_mock, patch(
                "materialize_probes.build_anchor_centroids"
            ) as build_anchor_centroids_mock:
                load_space_vectors_mock.side_effect = [
                    ({1: np.array([1, 0, 0, 0], dtype=np.float32)}, [1]),
                    ({2: np.array([0, 1, 0, 0], dtype=np.float32)}, [2]),
                ]
                build_anchor_centroids_mock.side_effect = [
                    {"a": np.array([1, 0, 0, 0], dtype=np.float32)},
                    {"b": np.array([0, 1, 0, 0], dtype=np.float32)},
                ]

                payloads = prepare_space_payloads(
                    conn,
                    conn,
                    embedding_metrics,
                    {"anchors": [{"anchor_id": "a"}, {"anchor_id": "b"}]},
                )

            self.assertEqual(len(payloads), 2)
            self.assertEqual(load_space_vectors_mock.call_count, 2)
            self.assertEqual(build_anchor_centroids_mock.call_count, 2)
        finally:
            conn.close()

    def test_repo_probe_configs_include_required_anchor_families(self):
        anchors_payload = yaml.safe_load((ROOT / "configs" / "anchors.yaml").read_text(encoding="utf-8"))
        probes_payload = yaml.safe_load((ROOT / "configs" / "probes.yaml").read_text(encoding="utf-8"))

        anchor_ids = {anchor["anchor_id"] for anchor in anchors_payload["anchors"]}
        pattern_ids = {pattern["pattern_id"] for pattern in probes_payload["patterns"]}

        self.assertTrue(
            {
                "queue_value_passive_quoting",
                "refill_lag_resiliency",
                "auction_handoff",
                "maker_retreat_inventory_stress",
                "parity_propagation_delayed_repair",
                "market_design_seams",
                "settlement_resolution_seams",
                "participant_pathologies",
                "state_graph_inconsistencies",
                "lifecycle_professionalization",
            }.issubset(anchor_ids)
        )
        self.assertTrue(
            {
                "near_transition_queue_refill",
                "near_transition_auction_refill",
                "near_transition_auction_queue",
                "near_transition_maker_queue",
                "near_transition_parity_repair",
                "near_market_design_far_realized",
                "near_settlement_resolution_far_realized",
                "near_participant_pathology_far_realized",
                "near_state_graph_far_realized",
                "near_lifecycle_far_realized",
            }.issubset(pattern_ids)
        )

    def test_probe_stage_writes_hits_and_canonical_probe_state(self):
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
                  ('p1', 'arxiv', 'parity anchor', 'cross-market parity anchor'),
                  ('p2', 'arxiv', 'parity neighbor', 'cross-market parity neighbor'),
                  ('p3', 'arxiv', 'dead end', 'theorem only dead end');
                INSERT INTO text_views (view_id, paper_id, view_type, text, token_estimate, text_sha256) VALUES
                  (1, 'p1', 'title_abs', 'parity anchor', 2, 'a'),
                  (2, 'p2', 'title_abs', 'parity neighbor', 2, 'b'),
                  (3, 'p3', 'title_abs', 'dead end', 2, 'c');
                INSERT INTO embedding_spaces (space_id, name, model_name, dims, normalized, prompt_style) VALUES
                  (1, 's1_title_abs_main', 'local-test', 4, 1, 'title_abs');
                """
            )
            conn.commit()
            conn.close()

            vec_db = tmp / "embeddings.sqlite3"
            vec_conn = connect_vec_store(vec_db)
            ensure_vec_table(vec_conn, "vec_s1_title_abs_main_4", 4)
            write_vectors(
                vec_conn,
                "vec_s1_title_abs_main_4",
                [1, 2, 3],
                np.array(
                    [
                        [1.0, 0.0, 0.0, 0.0],
                        [0.95, 0.05, 0.0, 0.0],
                        [0.0, 1.0, 0.0, 0.0],
                    ],
                    dtype=np.float32,
                ),
            )
            vec_conn.close()

            embedding_metrics = tmp / "embedding_metrics.json"
            embedding_metrics.write_text(
                json.dumps(
                    {
                        "run_id": "embed-run",
                        "vec_db_path": str(vec_db),
                        "spaces": [
                            {
                                "name": "s1_title_abs_main",
                                "view_type": "title_abs",
                                "dims": 4,
                                "table_name": "vec_s1_title_abs_main_4",
                                "view_count": 3,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            anchors = tmp / "anchors.yaml"
            anchors.write_text(
                """
anchors:
  - anchor_id: parity_propagation
    label: parity
    anchor_type: positive
    paper_ids: ["p1"]
    keywords: ["parity"]
    tags: [parity]
  - anchor_id: negative_anchor
    label: negative
    anchor_type: negative
    paper_ids: ["p3"]
    tags: [negative]
""".strip(),
                encoding="utf-8",
            )
            probes = tmp / "probes.yaml"
            probes.write_text(
                """
patterns:
  - pattern_id: near_parity_far_dead_end
    label: near parity, far dead-end
    kind: contrast
    include: [parity_propagation]
    exclude: [negative_anchor]
""".strip(),
                encoding="utf-8",
            )

            output_dir = tmp / "probe-run"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "materialize_probes.py"),
                    "--db-path",
                    str(canonical_db),
                    "--run-id",
                    "probe-run",
                    "--embedding-run-id",
                    "embed-run",
                    "--embedding-metrics-path",
                    str(embedding_metrics),
                    "--vec-db-path",
                    str(vec_db),
                    "--anchors-path",
                    str(anchors),
                    "--probes-path",
                    str(probes),
                    "--output-dir",
                    str(output_dir),
                    "--top-k",
                    "2",
                    "--candidate-pool",
                    "3",
                ],
                check=True,
                cwd=ROOT,
            )

            conn = sqlite3.connect(str(canonical_db))
            try:
                anchor_count = conn.execute("SELECT count(*) FROM anchors").fetchone()[0]
                pattern_count = conn.execute("SELECT count(*) FROM agitator_patterns").fetchone()[0]
                hit_count = conn.execute("SELECT count(*) FROM probe_hits WHERE run_id='probe-run'").fetchone()[0]
                top_view = conn.execute(
                    """
                    SELECT view_id
                    FROM probe_hits
                    WHERE run_id='probe-run' AND pattern_id='near_parity_far_dead_end' AND rank=1
                    """
                ).fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(anchor_count, 2)
            self.assertEqual(pattern_count, 1)
            self.assertEqual(hit_count, 2)
            self.assertEqual(top_view, 1)


if __name__ == "__main__":
    unittest.main()
