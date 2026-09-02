import json
import math
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))

import run_external_eod_screen as screen


class ExternalEodScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "research" / "external_driver_candidates.json").read_text(encoding="utf-8"))

    def test_batch_never_exceeds_starter_rate_budget(self):
        symbols, batch_count = screen.batch_symbols(self.manifest, 0, 35)
        self.assertGreaterEqual(batch_count, 2)
        self.assertLessEqual(len(symbols), 39)  # 35 candidates + four always-on controls
        for control in screen.BROAD_CONTROLS:
            self.assertIn(control, symbols)

    def test_torn_daily_returns_exclude_current_forming_candle(self):
        def ts(day):
            return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())

        rows = [
            {"timestamp": ts(date(2026, 8, 30)), "close": 100.0},
            {"timestamp": ts(date(2026, 8, 31)), "close": 110.0},
            {"timestamp": ts(date(2026, 9, 1)), "close": 121.0},
            {"timestamp": ts(date(2026, 9, 2)), "close": 500.0},  # forming: must be ignored
        ]
        returns = screen.torn_daily_return_series(rows, today_utc=date(2026, 9, 2))
        self.assertEqual(set(returns), {date(2026, 8, 31), date(2026, 9, 1)})
        self.assertAlmostEqual(returns[date(2026, 8, 31)], 0.10)
        self.assertAlmostEqual(returns[date(2026, 9, 1)], 0.10)

    def test_external_adjusted_and_raw_returns_are_distinct(self):
        rows = [
            {"date": "2026-01-01T00:00:00+00:00", "close": 100.0, "adjClose": 50.0},
            {"date": "2026-01-02T00:00:00+00:00", "close": 120.0, "adjClose": 55.0},
        ]
        raw = screen.external_return_series(rows, "raw")
        adjusted = screen.external_return_series(rows, "adjusted")
        self.assertAlmostEqual(raw[date(2026, 1, 2)], 0.20)
        self.assertAlmostEqual(adjusted[date(2026, 1, 2)], 0.10)

    def test_statistical_helpers_recover_linear_relationship(self):
        xs = [float(i) for i in range(1, 21)]
        ys = [2.0 + 3.0 * x for x in xs]
        self.assertAlmostEqual(screen.pearson(xs, ys), 1.0)
        self.assertAlmostEqual(screen.spearman(xs, ys), 1.0)
        regression = screen.simple_regression(xs, ys)
        self.assertAlmostEqual(regression["alpha"], 2.0)
        self.assertAlmostEqual(regression["beta"], 3.0)
        self.assertAlmostEqual(regression["r2"], 1.0)

    def test_incremental_r2_detects_candidate_information_over_control(self):
        n = 100
        control = [math.sin(i / 7) for i in range(n)]
        candidate = [math.cos(i / 9) for i in range(n)]
        y = [0.7 * c + 1.3 * x for c, x in zip(control, candidate)]
        control_r2 = screen.multiple_r2(y, [control])
        full_r2 = screen.multiple_r2(y, [control, candidate])
        self.assertIsNotNone(control_r2)
        self.assertIsNotNone(full_r2)
        self.assertGreater(full_r2 - control_r2, 0.2)
        self.assertAlmostEqual(full_r2, 1.0, places=10)

    def test_date_offset_alignment_is_explicit(self):
        torn = {date(2026, 1, 2): 0.1, date(2026, 1, 3): 0.2}
        external = {date(2026, 1, 3): 0.3, date(2026, 1, 4): 0.4}
        dates, ys, xs = screen.align_pair(torn, external, 1)
        self.assertEqual(dates, [date(2026, 1, 2), date(2026, 1, 3)])
        self.assertEqual(ys, [0.1, 0.2])
        self.assertEqual(xs, [0.3, 0.4])

    def test_persisted_result_schema_rejects_reconstructable_series(self):
        safe = [{"torn_symbol": "TSB", "external_symbol": "HSBC", "pearson": 0.5, "overlap_count": 1000}]
        unsafe = [{"torn_symbol": "TSB", "returns": [0.1, 0.2]}]
        self.assertTrue(screen.output_is_non_reconstructable(safe))
        self.assertFalse(screen.output_is_non_reconstructable(unsafe))

    def test_manifest_roles_include_broad_controls_for_all_stocks(self):
        roles = screen.relevant_torn_roles(self.manifest)
        spy_stocks = {row["torn_symbol"] for row in roles["SPY"] if row["candidate_role"] == "broad_control"}
        self.assertEqual(len(spy_stocks), 35)
        self.assertIn("TSB", spy_stocks)
        self.assertIn("PTS", spy_stocks)


if __name__ == "__main__":
    unittest.main()
