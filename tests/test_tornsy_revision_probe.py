import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))

import tornsy_revision_probe as probe


class TornsyRevisionProbeTests(unittest.TestCase):
    def test_validate_config_accepts_unique_closed_windows(self):
        windows = probe.validate_config(
            {
                "windows": [
                    {"name": "a", "interval": "m1", "from_ts": 1, "to_ts": 2},
                    {"name": "b", "interval": "d1", "from_ts": 3, "to_ts": 4},
                ]
            }
        )
        self.assertEqual([row["name"] for row in windows], ["a", "b"])

    def test_validate_config_rejects_duplicate_names(self):
        with self.assertRaises(probe.ResearchToolError):
            probe.validate_config(
                {
                    "windows": [
                        {"name": "a", "interval": "m1", "from_ts": 1, "to_ts": 2},
                        {"name": "a", "interval": "h1", "from_ts": 3, "to_ts": 4},
                    ]
                }
            )

    def test_extract_symbols_is_sorted_unique(self):
        payload = {"data": [{"stock": "LSC"}, {"stock": "ASS"}, {"stock": "LSC"}]}
        self.assertEqual(probe.extract_symbols(payload), ["ASS", "LSC"])

    def test_fingerprint_is_order_independent_after_normalization(self):
        payload_a = {"data": [[2, "2", 20], [1, "1", 10]]}
        payload_b = {"data": [[1, "1", 10], [2, "2", 20]]}
        first = probe.fingerprint(payload_a, "m1")
        second = probe.fingerprint(payload_b, "m1")
        self.assertEqual(first["semantic_sha256"], second["semantic_sha256"])
        self.assertEqual(first["rows"], 2)
        self.assertEqual(first["oldest_ts"], 1)
        self.assertEqual(first["newest_ts"], 2)

    def test_compare_baseline_detects_revision(self):
        current = [{"symbol": "ASS", "window": "w", "rows": 2, "semantic_sha256": "new"}]
        baseline = {
            "config_sha256": "cfg",
            "entries": [{"symbol": "ASS", "window": "w", "rows": 2, "semantic_sha256": "old"}],
        }
        result = probe.compare_baseline(current, baseline, "cfg")
        self.assertEqual(result["mismatches"], 1)
        self.assertEqual(result["comparisons"][0]["status"], "changed")

    def test_compare_baseline_accepts_identical_history(self):
        current = [{"symbol": "ASS", "window": "w", "rows": 2, "semantic_sha256": "same"}]
        baseline = {
            "config_sha256": "cfg",
            "entries": [{"symbol": "ASS", "window": "w", "rows": 2, "semantic_sha256": "same"}],
        }
        result = probe.compare_baseline(current, baseline, "cfg")
        self.assertEqual(result["mismatches"], 0)
        self.assertEqual(result["comparisons"][0]["status"], "unchanged")


if __name__ == "__main__":
    unittest.main()
