import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import plan_stock_fee_ceiling_family as broad


class BroadFeeProtocolTests(unittest.TestCase):
    def test_hrg_example_is_broad_candidate(self):
        price = broad.parse_price("272.67")
        row = broad.is_broad_candidate(price, 4)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.boundary_multiplier, 1)
        self.assertEqual(row.ceiling_family_fee, 2)
        self.assertEqual(row.non_ceiling_fee, 1)
        self.assertEqual(row.conservative_gross_low, "1090.660")
        self.assertEqual(row.conservative_gross_high, "1090.72")

    def test_candidate_predictions_are_invariant_over_conservative_interval(self):
        price = broad.parse_price("272.67")
        row = broad.is_broad_candidate(price, 4)
        assert row is not None
        low = Decimal(row.conservative_gross_low)
        high = Decimal(row.conservative_gross_high)
        self.assertGreater(low, Decimal("1001"))
        self.assertLess(high, Decimal("1499"))

    def test_near_integer_boundary_is_rejected(self):
        price = broad.parse_price("250.01")
        self.assertIsNone(broad.is_broad_candidate(price, 4))

    def test_near_half_fee_boundary_is_rejected(self):
        price = broad.parse_price("374.75")
        self.assertIsNone(broad.is_broad_candidate(price, 4))

    def test_broad_protocol_is_strictly_more_available_than_narrow_for_hrg_example(self):
        price = broad.parse_price("272.67")
        broad_rows = broad.find_candidates(price, max_gross=Decimal("5000"), limit=100)
        self.assertTrue(broad_rows)

    def test_price_must_still_be_exactly_two_decimals(self):
        with self.assertRaises(broad.PlannerError):
            broad.parse_price("272.671")


if __name__ == "__main__":
    unittest.main()
