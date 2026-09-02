import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import run_leave_one_out_factor as loo


class LeaveOneOutFactorTests(unittest.TestCase):
    def test_canonical_universe(self):
        symbols = loo.load_symbols(ROOT / "research" / "external_driver_candidates.json")
        self.assertEqual(len(symbols), 35); self.assertNotIn("TCSE", symbols)

    def test_returns_require_exact_previous_timestamp(self):
        rows = [
            {"timestamp": 0, "close": 100.0},
            {"timestamp": 3600, "close": 110.0},
            {"timestamp": 10800, "close": 121.0},
            {"timestamp": 14400, "close": 133.1},
        ]
        returns = loo.returns_from_rows(rows, "h1", now_ts=18000)
        self.assertIn(3600, returns); self.assertNotIn(10800, returns); self.assertIn(14400, returns)

    def test_factor_excludes_target(self):
        series = {"TARGET": {1: 100.0}}
        series.update({f"P{i}": {1: 1.0} for i in range(34)})
        factor = loo.leave_one_out_factor("TARGET", series, min_peers=30)
        self.assertEqual(factor[1], 1.0)

    def test_factor_requires_peer_coverage(self):
        series = {"TARGET": {1: 0.0}}
        series.update({f"P{i}": {1: 1.0} for i in range(29)})
        self.assertNotIn(1, loo.leave_one_out_factor("TARGET", series, min_peers=30))

    def test_regression_recovers_loading(self):
        factor = {i: (i-20)/1000 for i in range(50)}
        target = {i: .001 + 1.7*factor[i] for i in factor}
        stats = loo.regression(factor, target)
        self.assertAlmostEqual(stats["beta"], 1.7, places=10)
        self.assertAlmostEqual(stats["r2"], 1.0, places=10)

    def test_residualization_removes_exact_factor(self):
        factor = {i: (i-10)/1000 for i in range(30)}
        target = {i: .002 + 2*factor[i] for i in factor}
        residuals, stats = loo.residualize(target, factor)
        self.assertTrue(all(abs(x) < 1e-12 for x in residuals.values()))
        self.assertAlmostEqual(stats["residual_variance_ratio"], 0.0, places=10)

    def test_output_guard(self):
        self.assertTrue(loo.aggregate_guard([{"r2": .1, "horizon": "1h"}]))
        self.assertFalse(loo.aggregate_guard([{"returns": [.1, .2]}]))


if __name__ == "__main__": unittest.main()
