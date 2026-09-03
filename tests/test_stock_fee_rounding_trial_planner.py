import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import plan_stock_fee_rounding_trial as planner


class StockFeeRoundingTrialPlannerTests(unittest.TestCase):
    def test_price_requires_exactly_two_decimal_places(self):
        self.assertEqual(planner.parse_price("50.01"), Decimal("50.01"))
        for value in ("50", "50.0", "50.010", "0.00", "bad"):
            with self.assertRaises(planner.PlannerError):
                planner.parse_price(value)

    def test_known_50_01_candidate_is_robust(self):
        candidate = planner.is_robust_candidate(Decimal("50.01"), 20)
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.boundary_multiplier, 1)
        self.assertEqual(candidate.displayed_gross, "1000.20")
        self.assertEqual(candidate.conservative_gross_low, "1000.100")
        self.assertEqual(candidate.conservative_gross_high, "1000.40")
        self.assertEqual(candidate.lower_margin, "0.100")
        self.assertEqual(candidate.upper_margin, "0.10")
        self.assertEqual(candidate.reference_unrounded_total_ceiling_fee, 2)
        self.assertEqual(candidate.competing_rounded_gross_or_non_ceiling_fee, 1)

    def test_known_100_01_candidate_is_robust(self):
        candidate = planner.is_robust_candidate(Decimal("100.01"), 10)
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.displayed_gross, "1000.10")
        self.assertEqual(candidate.conservative_gross_low, "1000.050")
        self.assertEqual(candidate.conservative_gross_high, "1000.20")
        self.assertEqual(candidate.lower_margin, "0.050")
        self.assertEqual(candidate.upper_margin, "0.30")

    def test_candidate_rejects_boundary_and_half_dollar_ambiguity(self):
        # At exactly $1,000 displayed gross the conservative lower interval crosses
        # the fee boundary and is therefore not robust.
        self.assertIsNone(planner.is_robust_candidate(Decimal("50.00"), 20))
        # $1,000.40 displayed with 20 shares permits a conservative high gross of
        # $1,000.60, crossing the gross half-dollar rounding threshold.
        self.assertIsNone(planner.is_robust_candidate(Decimal("50.02"), 20))

    def test_every_returned_candidate_satisfies_strict_separation(self):
        price = Decimal("50.01")
        candidates = planner.find_candidates(price, max_shares=500, max_gross=Decimal("5000"), limit=20)
        self.assertGreaterEqual(len(candidates), 1)
        for candidate in candidates:
            k = Decimal(candidate.boundary_multiplier)
            boundary = Decimal("1000") * k
            low = (price - Decimal("0.005")) * Decimal(candidate.shares)
            high = (price + Decimal("0.01")) * Decimal(candidate.shares)
            self.assertGreater(low, boundary)
            self.assertLess(high, boundary + Decimal("0.50"))
            self.assertEqual(Decimal(candidate.conservative_gross_low), low)
            self.assertEqual(Decimal(candidate.conservative_gross_high), high)
            self.assertGreater(Decimal(candidate.lower_margin), 0)
            self.assertGreater(Decimal(candidate.upper_margin), 0)
            self.assertEqual(candidate.reference_unrounded_total_ceiling_fee, candidate.boundary_multiplier + 1)
            self.assertEqual(candidate.competing_rounded_gross_or_non_ceiling_fee, candidate.boundary_multiplier)

    def test_candidate_search_obeys_max_gross_and_limit(self):
        candidates = planner.find_candidates(
            Decimal("50.01"),
            max_shares=1000,
            max_gross=Decimal("2500"),
            limit=1,
        )
        self.assertEqual(len(candidates), 1)
        self.assertLessEqual(Decimal(candidates[0].displayed_gross), Decimal("2500"))

    def test_invalid_search_limits_are_rejected(self):
        for max_gross in (Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")):
            with self.assertRaises(planner.PlannerError):
                planner.find_candidates(Decimal("50.01"), max_gross=max_gross)
        with self.assertRaises(planner.PlannerError):
            planner.find_candidates(Decimal("50.01"), max_shares=0)
        with self.assertRaises(planner.PlannerError):
            planner.find_candidates(Decimal("50.01"), limit=0)

    def test_no_candidate_is_explicit(self):
        candidates = planner.find_candidates(
            Decimal("333.33"),
            max_shares=3,
            max_gross=Decimal("999.99"),
            limit=20,
        )
        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
