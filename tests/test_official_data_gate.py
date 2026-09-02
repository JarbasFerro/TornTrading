import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))

import run_official_data_gate as gate


class OfficialDataGateTests(unittest.TestCase):
    def test_choose_tornsy_interval_from_observed_cadence(self):
        self.assertEqual(gate.choose_tornsy_interval({"median_delta_s": 60}), "m1")
        self.assertEqual(gate.choose_tornsy_interval({"median_delta_s": 3600.0}), "h1")
        self.assertIsNone(gate.choose_tornsy_interval({"median_delta_s": 42}))
        self.assertIsNone(gate.choose_tornsy_interval({"median_delta_s": None}))

    def test_compare_at_offset_detects_one_minute_shift(self):
        official = [
            {"timestamp": 1000, "price": 10.0},
            {"timestamp": 1060, "price": 11.0},
            {"timestamp": 1120, "price": 12.0},
        ]
        archive = [
            {"timestamp": 1060, "price": 10.0},
            {"timestamp": 1120, "price": 11.0},
            {"timestamp": 1180, "price": 12.0},
        ]
        zero = gate.compare_at_offset(official, archive, interval="m1", offset_seconds=0)
        plus_60 = gate.compare_at_offset(official, archive, interval="m1", offset_seconds=60)
        self.assertLess(zero["numeric_equal_pct"], 100.0)
        self.assertEqual(plus_60["comparable_pairs"], 3)
        self.assertEqual(plus_60["numeric_equal_pct"], 100.0)
        self.assertEqual(plus_60["mean_abs_price_diff"], 0.0)

    def test_choose_best_offset_prefers_exact_zero_difference(self):
        candidates = [
            {
                "offset_seconds": 0,
                "comparable_pairs": 20,
                "numeric_equal_pct": 100.0,
                "mean_abs_price_diff": 0.0,
            },
            {
                "offset_seconds": 60,
                "comparable_pairs": 20,
                "numeric_equal_pct": 100.0,
                "mean_abs_price_diff": 0.01,
            },
        ]
        self.assertEqual(gate.choose_best_offset(candidates)["offset_seconds"], 0)

    def test_aggregate_does_not_overstate_unresolved_stocks(self):
        rows = [
            {
                "best_offset_seconds": 0,
                "best_numeric_equal_pct": 100.0,
                "tornsy_interval": "m1",
            },
            {
                "best_offset_seconds": 60,
                "best_numeric_equal_pct": 95.0,
                "tornsy_interval": "m1",
            },
            {
                "best_offset_seconds": None,
                "best_numeric_equal_pct": None,
                "tornsy_interval": None,
            },
        ]
        summary = gate.build_aggregate(rows)
        self.assertEqual(summary["stocks_total"], 3)
        self.assertEqual(summary["stocks_with_comparable_history"], 2)
        self.assertEqual(summary["stocks_without_comparable_history"], 1)
        self.assertEqual(summary["stocks_exact_at_zero_offset"], 1)
        self.assertEqual(summary["observed_official_intervals"], ["m1"])


if __name__ == "__main__":
    unittest.main()
