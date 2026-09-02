import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))

import run_tcse_factor as factor


class TcseFactorTests(unittest.TestCase):
    def test_manifest_universe_is_35_and_excludes_tcse(self):
        symbols = factor.load_tradable_symbols(ROOT / "research" / "external_driver_candidates.json")
        self.assertEqual(len(symbols), 35)
        self.assertNotIn("TCSE", symbols)

    def test_one_period_returns_require_exact_timestamp(self):
        prices = {0: 100.0, 3600: 110.0, 10800: 121.0, 14400: 133.1}
        returns = factor.one_period_returns(prices, 3600)
        self.assertIn(3600, returns)
        self.assertNotIn(10800, returns)
        self.assertIn(14400, returns)

    def test_regression_recovers_factor_loading(self):
        x = [i / 100.0 for i in range(-20, 21)]
        y = [0.001 + 1.5 * v for v in x]
        stats = factor.simple_regression(x, y)
        self.assertAlmostEqual(stats["alpha"], 0.001, places=12)
        self.assertAlmostEqual(stats["beta"], 1.5, places=12)
        self.assertAlmostEqual(stats["r2"], 1.0, places=12)

    def test_residualization_removes_exact_common_factor(self):
        market = {i: (i - 10) / 1000 for i in range(30)}
        stock = {i: 0.002 + 2.0 * market[i] for i in market}
        residuals, stats = factor.residualize(stock, market)
        self.assertAlmostEqual(stats["r2"], 1.0, places=12)
        self.assertTrue(all(abs(v) < 1e-12 for v in residuals.values()))
        self.assertAlmostEqual(stats["residual_variance_ratio"], 0.0, places=12)

    def test_equal_weight_market_requires_minimum_coverage(self):
        series = {
            f"S{i}": {1: i / 1000, 2: i / 900}
            for i in range(35)
        }
        for i in range(10):
            del series[f"S{i}"][2]
        market = factor.equal_weight_market(series, min_stocks=30)
        self.assertIn(1, market)
        self.assertNotIn(2, market)

    def test_factor_removal_reduces_pairwise_correlation(self):
        market = {i: ((i % 13) - 6) / 1000 for i in range(100)}
        stocks = {}
        residuals = {}
        for j in range(5):
            stock = {i: 1.2 * market[i] + (((i * (j + 3)) % 17) - 8) / 10000 for i in market}
            stocks[str(j)] = stock
            residuals[str(j)], _ = factor.residualize(stock, market)
        raw = factor.mean_pairwise_correlation(stocks)
        resid = factor.mean_pairwise_correlation(residuals)
        self.assertGreater(raw["mean_pairwise_pearson"], resid["mean_pairwise_pearson"])

    def test_chronological_quartiles_return_four_segments(self):
        market = {i: i / 10000 for i in range(100)}
        stock = {i: 0.5 * market[i] + (i % 7) / 100000 for i in market}
        rows = factor.chronological_quartiles(stock, market)
        self.assertEqual(len(rows), 4)
        self.assertEqual(sum(row["count"] for row in rows), 100)

    def test_output_guard_rejects_series(self):
        self.assertTrue(factor.aggregate_guard([{"horizon": "1h", "r2": 0.2}]))
        self.assertFalse(factor.aggregate_guard([{"returns": [0.1, 0.2]}]))


if __name__ == "__main__":
    unittest.main()
