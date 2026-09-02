import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))

import run_tornsy_matrix as matrix


class TornsyMatrixTests(unittest.TestCase):
    def test_extract_watchlist_symbols_is_sorted_and_unique(self):
        payload = {
            "data": [
                {"stock": "LSC", "price": "1"},
                {"stock": "ASS", "price": "2"},
                {"stock": "LSC", "price": "3"},
            ]
        }
        self.assertEqual(matrix.extract_watchlist_symbols(payload), ["ASS", "LSC"])

    def test_extract_watchlist_symbols_rejects_invalid_shape(self):
        with self.assertRaises(matrix.ResearchToolError):
            matrix.extract_watchlist_symbols({"stocks": []})

    def test_build_summary_preserves_errors_and_interval_totals(self):
        rows = [
            {
                "symbol": "ASS",
                "interval": "m1",
                "rows": 2000,
                "duplicates": 0,
                "max_delta_s": 120,
                "missing_slots_if_regular": 1,
                "error": None,
            },
            {
                "symbol": "LSC",
                "interval": "m1",
                "rows": None,
                "duplicates": None,
                "max_delta_s": None,
                "missing_slots_if_regular": None,
                "error": "temporary failure",
            },
        ]
        summary = matrix.build_summary(rows, ["ASS", "LSC"], ["m1"])
        self.assertEqual(summary["requests_expected"], 2)
        self.assertEqual(summary["requests_successful"], 1)
        self.assertEqual(summary["requests_failed"], 1)
        self.assertEqual(summary["by_interval"]["m1"]["successful_symbols"], 1)
        self.assertEqual(summary["by_interval"]["m1"]["error_symbols"], 1)
        self.assertEqual(summary["by_interval"]["m1"]["total_regular_missing_slots"], 1)


if __name__ == "__main__":
    unittest.main()
