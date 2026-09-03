import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import snapshot_live_fee_trial_candidates as live


def stock(stock_id, acronym, name, price):
    return {
        "id": stock_id,
        "acronym": acronym,
        "name": name,
        "market": {"price": price, "cap": 1, "shares": 1, "investors": 1},
    }


class LiveFeeTrialCandidateTests(unittest.TestCase):
    def test_official_price_normalizes_cent_value_to_two_decimals(self):
        self.assertEqual(str(live.official_price(stock(1, "AAA", "A", 50.1))), "50.10")

    def test_official_price_rejects_sub_cent_precision(self):
        with self.assertRaises(ValueError):
            live.official_price(stock(1, "AAA", "A", 50.123))

    def test_tcse_is_excluded(self):
        rows = [stock(1, "TCSE", "Index", 50.01), stock(2, "AAA", "A", 50.01)]
        candidates = live.build_candidates(rows)
        self.assertTrue(candidates)
        self.assertNotIn("TCSE", {candidate.stock_acronym for candidate in candidates})

    def test_every_candidate_revalidates_through_frozen_planner(self):
        rows = [
            stock(1, "AAA", "A", 50.01),
            stock(2, "BBB", "B", 100.01),
            stock(3, "CCC", "C", 150.01),
            stock(4, "DDD", "D", 200.01),
            stock(5, "EEE", "E", 300.01),
        ]
        candidates = live.build_candidates(rows)
        self.assertTrue(candidates)
        for candidate in candidates:
            live.assert_candidate(candidate.__dict__)

    def test_suggested_six_spans_three_boundaries(self):
        rows = [
            stock(1, "A01", "A1", 50.01),
            stock(2, "A02", "A2", 100.01),
            stock(3, "B01", "B1", 100.01),
            stock(4, "B02", "B2", 200.01),
            stock(5, "C01", "C1", 150.01),
            stock(6, "C02", "C2", 300.01),
        ]
        candidates = live.build_candidates(rows)
        suggested = live.choose_suggested_six(candidates)
        self.assertEqual(len(suggested), 6)
        self.assertGreaterEqual(len({row["boundary_multiplier"] for row in suggested}), 3)
        self.assertGreaterEqual(len({row["stock_id"] for row in suggested}), 2)
        for row in suggested:
            live.assert_candidate(row)

    def test_report_is_public_plan_and_safe(self):
        rows = [
            stock(1, "A01", "A1", 50.01),
            stock(2, "A02", "A2", 100.01),
            stock(3, "B01", "B1", 100.01),
            stock(4, "B02", "B2", 200.01),
            stock(5, "C01", "C1", 150.01),
            stock(6, "C02", "C2", 300.01),
        ]
        report = live.build_report(rows, server_timestamp=1788464000, retrieved_at="2026-09-03T17:20:00.000Z")
        self.assertEqual(report["research_status"], "LIVE_PUBLIC_EXPERIMENT_PLAN_SNAPSHOT")
        self.assertEqual(len(report["suggested_six"]), 6)
        live.assert_safe_report(report)

    def test_stale_or_nonqualifying_prices_need_no_candidate(self):
        rows = [stock(1, "AAA", "A", 333.33)]
        report = live.build_report(rows, server_timestamp=1788464000, retrieved_at="2026-09-03T17:20:00.000Z")
        # A candidate may or may not exist at a higher K; the important contract is
        # that every persisted candidate must satisfy the frozen planner exactly.
        for group in report["candidates_by_boundary"].values():
            for row in group:
                live.assert_candidate(row)


if __name__ == "__main__":
    unittest.main()
