import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import analyze_stock_sell_fee_rounding as fee


class StockSellFeeRoundingTests(unittest.TestCase):
    def test_parse_current_v2_stock_sell_log(self):
        payload = {
            "log": [
                {
                    "id": "private-event-id",
                    "timestamp": 1770000000,
                    "details": {"id": 5511, "title": "Stock sell", "category": "Stocks"},
                    "data": {
                        "amount": 1001,
                        "price": "18.981",
                        "fees": 18,
                        "profit": 123456789,
                        "stock": 42,
                    },
                    "params": {},
                }
            ]
        }
        sales, rejected = fee.extract_sales(payload)
        self.assertEqual(rejected, 0)
        self.assertEqual(
            sales,
            [fee.SaleObservation(amount=1001, price=Decimal("18.981"), fee=18)],
        )

    def test_parse_decimal_accepts_currency_format_without_float_conversion(self):
        self.assertEqual(fee.parse_decimal("$12,345.6789"), Decimal("12345.6789"))

    def test_wrong_log_type_and_invalid_values_are_rejected(self):
        payload = {
            "log": [
                {"details": {"id": 5510}, "data": {"amount": 1, "price": "10", "fees": 0}},
                {"details": {"id": 5511}, "data": {"amount": 0, "price": "10", "fees": 0}},
                {"details": {"id": 5511}, "data": {"amount": 1, "price": "bad", "fees": 0}},
            ]
        }
        sales, rejected = fee.extract_sales(payload)
        self.assertEqual(sales, [])
        self.assertEqual(rejected, 3)

    def test_frozen_model_family_collapses_only_proven_exact_redundancies(self):
        names = {model.name for model in fee.build_models()}
        self.assertEqual(len(names), 25)
        self.assertNotIn("gross_floor__fee_floor", names)
        self.assertNotIn("gross_ceiling__fee_ceiling", names)
        self.assertNotIn("gross_floor__fee_half_up", names)
        self.assertIn("total_value__fee_floor", names)
        self.assertIn("total_value__fee_ceiling", names)
        self.assertIn("total_value__fee_half_up", names)
        self.assertIn("total_value__fee_half_even", names)

    def test_pairwise_separation_measures_nearest_competitor_not_global_activity(self):
        vectors = {
            "winner": (1, 1, 1, 1, 1, 1),
            "near": (2, 1, 1, 1, 1, 1),
            "far": (2, 2, 2, 2, 2, 2),
        }
        self.assertEqual(fee.discriminating_observation_count(vectors), 6)
        self.assertEqual(fee.minimum_pairwise_separation(vectors, "winner"), 1)

    def test_six_strong_synthetic_observations_identify_total_value_floor(self):
        observations = [
            fee.SaleObservation(1001, Decimal("18.981"), 18),
            fee.SaleObservation(273, Decimal("62.27"), 16),
            fee.SaleObservation(999, Decimal("66.066"), 65),
            fee.SaleObservation(1001, Decimal("91.908"), 91),
            fee.SaleObservation(99, Decimal("111.107"), 10),
            fee.SaleObservation(154, Decimal("129.868"), 19),
        ]
        report = fee.analyze(
            observations,
            0,
            lookback_days=365,
            retrieved_at="2026-09-03T05:30:00.000Z",
        )
        self.assertEqual(report["decision_status"], "UNIQUE_PERFECT_MODEL")
        self.assertEqual(report["perfect_models"], ["total_value__fee_floor"])
        self.assertEqual(report["discriminating_observations"], 6)
        self.assertGreaterEqual(report["winner_minimum_pairwise_separation"], 6)

    def test_less_than_six_discriminating_observations_cannot_close_gate(self):
        observation = fee.SaleObservation(1001, Decimal("18.981"), 18)
        report = fee.analyze(
            [observation],
            0,
            lookback_days=365,
            retrieved_at="2026-09-03T05:30:00.000Z",
        )
        self.assertEqual(report["decision_status"], "INSUFFICIENT_DISCRIMINATION")

    def test_no_usable_observations_is_explicit(self):
        report = fee.analyze(
            [],
            3,
            lookback_days=365,
            retrieved_at="2026-09-03T05:30:00.000Z",
        )
        self.assertEqual(report["decision_status"], "NO_USABLE_OBSERVATIONS")
        self.assertEqual(report["usable_observations"], 0)
        self.assertEqual(report["rejected_observations"], 3)
        self.assertIsNone(report["winner_minimum_pairwise_separation"])

    def test_public_report_contains_no_private_trade_values(self):
        observations = [
            fee.SaleObservation(1001, Decimal("18981.1234567"), 19000123),
            fee.SaleObservation(273, Decimal("62270.7654321"), 17000123),
        ]
        report = fee.analyze(
            observations,
            0,
            lookback_days=365,
            retrieved_at="2026-09-03T05:30:00.000Z",
        )
        serialized = repr(report)
        for forbidden in (
            "18981.1234567",
            "62270.7654321",
            "19000123",
            "17000123",
            "private-event-id",
            "123456789",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_safe_report_rejects_raw_trade_field(self):
        report = fee.analyze(
            [],
            0,
            lookback_days=365,
            retrieved_at="2026-09-03T05:30:00.000Z",
        )
        report["raw_trades"] = []
        with self.assertRaises(fee.ResearchToolError):
            fee.assert_safe_report(report)

    def test_write_report_keeps_aggregate_structure_only(self):
        report = fee.analyze(
            [],
            0,
            lookback_days=365,
            retrieved_at="2026-09-03T05:30:00.000Z",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            fee.write_report(path, report)
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("raw_trades", text)
            self.assertNotIn("event_timestamp", text)
            self.assertNotIn("stock_id", text)
            self.assertNotIn("share_count", text)
            self.assertNotIn("observed_fee", text)


if __name__ == "__main__":
    unittest.main()
