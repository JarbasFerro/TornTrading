import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import diagnose_stock_sell_execution_timing as timing


class StockSellExecutionTimingTests(unittest.TestCase):
    def test_second_buckets_are_frozen(self):
        base = 1_800_000_000 - (1_800_000_000 % 60)
        expected = {
            0: "S00_02", 2: "S00_02",
            3: "S03_09", 9: "S03_09",
            10: "S10_49", 49: "S10_49",
            50: "S50_59", 59: "S50_59",
        }
        for second, label in expected.items():
            self.assertEqual(timing.second_bucket(base + second), label)

    def test_parse_sale_uses_only_current_stock_sell_shape(self):
        entry = {
            "id": "PRIVATE",
            "timestamp": 1_800_000_001,
            "details": {"id": 5511, "title": "Stock sell"},
            "data": {"stock": 7, "price": "50.01", "amount": 999, "fees": 123, "profit": 456},
        }
        sale = timing.parse_sale(entry)
        self.assertEqual(
            sale,
            timing.SaleEvent(timestamp=1_800_000_001, stock_id=7, logged_price=Decimal("50.01")),
        )

    def test_changed_boundary_current_and_previous_matches_are_distinct(self):
        minute = 1_800_000_000 - (1_800_000_000 % 60)
        prices = {
            minute - 60: Decimal("50.00"),
            minute: Decimal("50.01"),
            minute + 60: Decimal("50.02"),
        }
        current = timing.classify_sale(timing.SaleEvent(minute + 1, 1, Decimal("50.01")), prices)
        previous = timing.classify_sale(timing.SaleEvent(minute + 1, 1, Decimal("50.00")), prices)
        self.assertTrue(current.changed_boundary)
        self.assertEqual(current.match_pattern, "CURRENT_ONLY")
        self.assertEqual(previous.match_pattern, "PREVIOUS_ONLY")

    def test_flat_boundary_is_multi_match_not_timing_evidence(self):
        minute = 1_800_000_000 - (1_800_000_000 % 60)
        prices = {
            minute - 60: Decimal("50.00"),
            minute: Decimal("50.00"),
            minute + 60: Decimal("50.01"),
        }
        event = timing.classify_sale(timing.SaleEvent(minute + 1, 1, Decimal("50.00")), prices)
        self.assertFalse(event.changed_boundary)
        self.assertEqual(event.match_pattern, "PREVIOUS_CURRENT")

    def test_missing_exact_minute_is_source_incomplete(self):
        minute = 1_800_000_000 - (1_800_000_000 % 60)
        event = timing.classify_sale(
            timing.SaleEvent(minute + 1, 1, Decimal("50.01")),
            {minute - 60: Decimal("50.00"), minute: Decimal("50.01")},
        )
        self.assertFalse(event.source_complete)
        self.assertIsNone(event.match_pattern)

    def test_aggregate_detects_previous_price_early_clue(self):
        events = [
            timing.ClassifiedEvent("S00_02", True, "PREVIOUS_ONLY", True),
            timing.ClassifiedEvent("S00_02", True, "CURRENT_ONLY", True),
            timing.ClassifiedEvent("S10_49", True, "CURRENT_ONLY", True),
            timing.ClassifiedEvent("S50_59", False, None, False),
        ]
        report = timing.aggregate(
            events,
            metadata={
                "official_sell_log_rows": 4,
                "usable_sales": 4,
                "rejected_sales": 0,
                "unknown_stock_metadata": 0,
                "tornsy_requests": 4,
                "tornsy_errors": 0,
            },
            retrieved_at="2026-09-03T06:00:00.000Z",
        )
        self.assertEqual(
            report["diagnostic_label"],
            "PREVIOUS_MINUTE_RECEIPT_OBSERVED_IN_EARLY_POST_BOUNDARY_LOG_TIME",
        )
        self.assertEqual(report["primary_early_boundary"]["previous_only"], 1)
        self.assertEqual(report["source_incomplete_observations"], 1)

    def test_all_early_changed_current_is_nonconfirmatory_current_clue(self):
        events = [
            timing.ClassifiedEvent("S00_02", True, "CURRENT_ONLY", True),
            timing.ClassifiedEvent("S00_02", True, "CURRENT_ONLY", True),
        ]
        report = timing.aggregate(
            events,
            metadata={
                "official_sell_log_rows": 2,
                "usable_sales": 2,
                "rejected_sales": 0,
                "unknown_stock_metadata": 0,
                "tornsy_requests": 2,
                "tornsy_errors": 0,
            },
            retrieved_at="2026-09-03T06:00:00.000Z",
        )
        self.assertEqual(report["diagnostic_label"], "EARLY_CHANGED_BOUNDARY_RECEIPTS_ALL_MATCH_CURRENT_MINUTE")

    def test_report_schema_rejects_private_event_fields(self):
        report = timing.aggregate(
            [],
            metadata={
                "official_sell_log_rows": 0,
                "usable_sales": 0,
                "rejected_sales": 0,
                "unknown_stock_metadata": 0,
                "tornsy_requests": 0,
                "tornsy_errors": 0,
            },
            retrieved_at="2026-09-03T06:00:00.000Z",
        )
        report["event_timestamp"] = 1_800_000_001
        with self.assertRaises(timing.ResearchToolError):
            timing.assert_safe_report(report)

    def test_price_map_requires_exact_timestamp_rows(self):
        rows = [
            {"timestamp": 100, "price": 50.001},
            {"timestamp": 160, "price": 50.019},
        ]
        self.assertEqual(
            timing.price_map(rows),
            {100: Decimal("50.00"), 160: Decimal("50.02")},
        )


if __name__ == "__main__":
    unittest.main()
