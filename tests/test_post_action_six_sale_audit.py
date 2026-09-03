import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import audit_post_action_six_sales as audit


def entry(*, event_id, timestamp, stock, amount, price, fee):
    return {
        "id": event_id,
        "timestamp": timestamp,
        "details": {"id": 5511, "title": "Stock sell", "category": "Stocks"},
        "data": {
            "stock": stock,
            "amount": amount,
            "price": price,
            "fees": fee,
            "profit": 999999999,
        },
        "params": {},
    }


class PostActionSixSaleAuditTests(unittest.TestCase):
    def test_selection_is_exact_latest_six_after_protocol_merge(self):
        payload = {"log": [
            entry(event_id=f"id-{i}", timestamp=audit.PROTOCOL_MERGE_TS + i, stock=i, amount=1, price="1000.10", fee=2)
            for i in range(1, 9)
        ]}
        selected, usable = audit.select_latest_six(payload)
        self.assertEqual(usable, 8)
        self.assertEqual(len(selected), 6)
        self.assertEqual([sale.timestamp for sale in selected], sorted([audit.PROTOCOL_MERGE_TS + i for i in range(3, 9)], reverse=True))

    def test_preprotocol_and_wrong_log_entries_are_not_selected(self):
        payload = {"log": [
            entry(event_id="old", timestamp=audit.PROTOCOL_MERGE_TS - 1, stock=1, amount=1, price="1000.10", fee=2),
            {"timestamp": audit.PROTOCOL_MERGE_TS + 1, "details": {"id": 5510}, "data": {"stock": 2, "amount": 1, "price": "1000.10", "fees": 2}},
        ]}
        selected, usable = audit.select_latest_six(payload)
        self.assertEqual(selected, [])
        self.assertEqual(usable, 0)

    def test_known_geometry_is_detected(self):
        sale = audit.PrivateSale(
            observation=audit.base.SaleObservation(amount=20, price=Decimal("50.01"), fee=2),
            timestamp=audit.PROTOCOL_MERGE_TS + 20,
            stock_id=1,
        )
        qualifies, k = audit.boundary_geometry(sale)
        self.assertTrue(qualifies)
        self.assertEqual(k, 1)

    def test_boundary_crossing_geometry_is_rejected(self):
        sale = audit.PrivateSale(
            observation=audit.base.SaleObservation(amount=20, price=Decimal("50.00"), fee=1),
            timestamp=audit.PROTOCOL_MERGE_TS + 20,
            stock_id=1,
        )
        qualifies, _ = audit.boundary_geometry(sale)
        self.assertFalse(qualifies)

    def test_report_classifies_ceiling_support_but_remains_nonconfirmatory(self):
        sales = [
            audit.PrivateSale(
                observation=audit.base.SaleObservation(amount=20, price=Decimal("50.01"), fee=2),
                timestamp=audit.PROTOCOL_MERGE_TS + 20 + i * 60,
                stock_id=i + 1,
            )
            for i in range(6)
        ]
        report = audit.build_report(sales, usable_returned=6, retrieved_at="2026-09-03T17:10:00.000Z")
        self.assertEqual(report["selected_latest_sales"], 6)
        self.assertEqual(report["distinct_stock_count"], 6)
        self.assertEqual(report["targeted_geometry_count"], 6)
        self.assertEqual(report["targeted_geometry_fee_support"]["ceiling_k_plus_1"], 6)
        self.assertEqual(report["audit_conclusion"], "POST_ACTION_GEOMETRY_SUPPORTS_CEILING")
        self.assertFalse(report["preclick_plan_recorded"])
        self.assertFalse(report["confirmatory_eligible"])

    def test_report_classifies_competitor_support(self):
        sales = [
            audit.PrivateSale(
                observation=audit.base.SaleObservation(amount=20, price=Decimal("50.01"), fee=1),
                timestamp=audit.PROTOCOL_MERGE_TS + 20 + i * 60,
                stock_id=i + 1,
            )
            for i in range(6)
        ]
        report = audit.build_report(sales, usable_returned=6, retrieved_at="2026-09-03T17:10:00.000Z")
        self.assertEqual(report["audit_conclusion"], "POST_ACTION_GEOMETRY_SUPPORTS_COMPETITOR")

    def test_no_target_geometry_is_explicit(self):
        sales = [
            audit.PrivateSale(
                observation=audit.base.SaleObservation(amount=1, price=Decimal("50.00"), fee=1),
                timestamp=audit.PROTOCOL_MERGE_TS + 20 + i * 60,
                stock_id=i + 1,
            )
            for i in range(6)
        ]
        report = audit.build_report(sales, usable_returned=6, retrieved_at="2026-09-03T17:10:00.000Z")
        self.assertEqual(report["audit_conclusion"], "SIX_SALES_OBSERVED_NONE_TARGET_GEOMETRY")

    def test_aggregate_report_does_not_persist_private_trade_values(self):
        sales = [
            audit.PrivateSale(
                observation=audit.base.SaleObservation(amount=987654, price=Decimal("12345.67"), fee=12193254),
                timestamp=1788463337,
                stock_id=777,
            )
        ]
        report = audit.build_report(sales, usable_returned=1, retrieved_at="2026-09-03T17:10:00.000Z")
        serialized = repr(report)
        for forbidden in ("987654", "12345.67", "12193254", "1788463337", "777"):
            self.assertNotIn(forbidden, serialized)

    def test_safe_report_rejects_transaction_level_field(self):
        report = audit.build_report([], usable_returned=0, retrieved_at="2026-09-03T17:10:00.000Z")
        report["trades"] = []
        with self.assertRaises(audit.ResearchToolError):
            audit.assert_safe_report(report)


if __name__ == "__main__":
    unittest.main()
