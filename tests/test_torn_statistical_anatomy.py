import json
import math
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))

import run_torn_statistical_anatomy as anatomy


class TornStatisticalAnatomyTests(unittest.TestCase):
    def test_horizon_contract_is_exact(self):
        self.assertEqual(list(anatomy.HORIZONS), ["1m", "5m", "1h", "6h", "24h", "7d", "30d"])
        self.assertEqual(anatomy.HORIZONS["7d"], ("d1", 7))
        self.assertEqual(anatomy.HORIZONS["30d"], ("d1", 30))

    def test_manifest_has_35_tradable_symbols_and_excludes_tcse(self):
        symbols = anatomy.load_tradable_symbols(ROOT / "research" / "external_driver_candidates.json")
        self.assertEqual(len(symbols), 35)
        self.assertNotIn("TCSE", symbols)

    def test_closed_price_series_excludes_forming_period(self):
        rows = [
            {"timestamp": 0, "close": 100.0},
            {"timestamp": 86400, "close": 110.0},
            {"timestamp": 172800, "close": 121.0},
        ]
        points = anatomy.closed_price_series(rows, "d1", now_ts=172800 + 3600)
        self.assertEqual(points, [(0, 100.0), (86400, 110.0)])

    def test_lagged_returns_support_exact_multi_day_horizons(self):
        series = [(i * 86400, 100.0 * (1.01 ** i)) for i in range(40)]
        seven = anatomy.lagged_returns(series, 7, 86400)
        thirty = anatomy.lagged_returns(series, 30, 86400)
        self.assertEqual(len(seven), 33)
        self.assertEqual(len(thirty), 10)
        self.assertAlmostEqual(seven[0][1], 1.01 ** 7 - 1.0)
        self.assertAlmostEqual(thirty[0][1], 1.01 ** 30 - 1.0)

    def test_lagged_returns_do_not_bridge_source_gaps(self):
        # Missing timestamp 120 means the 60->180 move spans 120 seconds and
        # must not be mislabeled as a one-minute return.
        series = [(0, 100.0), (60, 101.0), (180, 103.0), (240, 104.0)]
        returns = anatomy.lagged_returns(series, 1, 60)
        timestamps = [ts for ts, _ in returns]
        self.assertEqual(timestamps, [60, 240])
        self.assertNotIn(180, timestamps)

    def test_distribution_stats_capture_basic_shape(self):
        values = [-0.02, -0.01, 0.0, 0.01, 0.02]
        stats = anatomy.distribution_stats(values)
        self.assertEqual(stats["count"], 5)
        self.assertAlmostEqual(stats["mean"], 0.0)
        self.assertAlmostEqual(stats["median"], 0.0)
        self.assertAlmostEqual(stats["positive_rate"], 0.4)
        self.assertAlmostEqual(stats["negative_rate"], 0.4)
        self.assertAlmostEqual(stats["zero_rate"], 0.2)

    def test_autocorrelation_detects_persistent_series(self):
        values = [float(i) for i in range(1, 100)]
        corr = anatomy.autocorrelation(values, 1)
        self.assertIsNotNone(corr)
        self.assertGreater(corr, 0.99)

    def test_continuation_reversal_stats_detect_continuation(self):
        values = [0.01, 0.02, 0.01, -0.01, -0.02, -0.01]
        stats = anatomy.continuation_reversal_stats(values)
        self.assertEqual(stats["transition_count"], 5)
        self.assertGreater(stats["continuation_rate"], 0.5)
        self.assertLess(stats["mean_next_after_negative"], 0)

    def test_pairwise_alignment_uses_common_timestamps_only(self):
        left = {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}
        right = {2: 1.0, 3: 2.0, 4: 3.0, 5: 4.0}
        count, corr = anatomy.pearson_aligned(left, right)
        self.assertEqual(count, 3)
        self.assertAlmostEqual(corr, 1.0)

    def test_quartile_stability_returns_four_segments(self):
        values = [math.sin(i / 4) / 100 for i in range(100)]
        rows = anatomy.quartile_stability(values)
        self.assertEqual(len(rows), 4)
        self.assertEqual(sum(row["count"] for row in rows), 100)

    def test_output_schema_guard_rejects_raw_series(self):
        safe = [{"torn_symbol": "TSB", "horizon": "1h", "mean": 0.001}]
        unsafe = [{"torn_symbol": "TSB", "returns": [0.1, 0.2]}]
        self.assertTrue(anatomy.output_schema_is_aggregate(safe))
        self.assertFalse(anatomy.output_schema_is_aggregate(unsafe))


if __name__ == "__main__":
    unittest.main()
