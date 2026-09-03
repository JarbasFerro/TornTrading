import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import audit_p0_e5b_hrg_trial as audit


def sell(ts=1788465740, fee=2, price="272.67", amount=4, stock=16):
    return {"timestamp": ts, "details": {"id": 5511}, "data": {"amount": amount, "price": price, "fees": fee, "profit": 0, "stock": stock}}


def buy(ts=1788465730, stock=16):
    return {"timestamp": ts, "details": {"id": 5510}, "data": {"amount": 4, "price": "272.67", "stock": stock}}


class P0E5bHrgTrialAuditTests(unittest.TestCase):
    def stocks(self):
        return [{"id": 16, "acronym": "HRG", "name": "Home Retail Group", "market": {"price": 272.67}}]

    def test_valid_receipt_supports_ceiling_family(self):
        report = audit.build_report(
            stocks=self.stocks(),
            sells_payload={"log": [sell(fee=2)]},
            buys_payload={"log": []},
            retrieved_at="2026-09-03T20:10:00Z",
        )
        self.assertEqual(report["trial_validity"], "VALID")
        self.assertEqual(report["observed_fee_class"], "CEILING_K_PLUS_1")
        self.assertEqual(report["formal_confirmation_status"], "SUPPORTING_NOT_FORMAL_COUNT")

    def test_non_ceiling_receipt_is_classified(self):
        report = audit.build_report(
            stocks=self.stocks(),
            sells_payload={"log": [sell(fee=1)]},
            buys_payload={"log": []},
            retrieved_at="2026-09-03T20:10:00Z",
        )
        self.assertEqual(report["trial_validity"], "VALID")
        self.assertEqual(report["observed_fee_class"], "NON_CEILING_K")

    def test_same_minute_buy_invalidates_control(self):
        report = audit.build_report(
            stocks=self.stocks(),
            sells_payload={"log": [sell(fee=2)]},
            buys_payload={"log": [buy()]},
            retrieved_at="2026-09-03T20:10:00Z",
        )
        self.assertEqual(report["trial_validity"], "INVALID_CONTROL_FAILURE")
        self.assertEqual(report["other_buy_sell_same_minute"], 1)

    def test_wrong_price_does_not_match_planned_receipt(self):
        report = audit.build_report(
            stocks=self.stocks(),
            sells_payload={"log": [sell(fee=2, price="272.68")]},
            buys_payload={"log": []},
            retrieved_at="2026-09-03T20:10:00Z",
        )
        self.assertEqual(report["trial_validity"], "INVALID_NO_RECEIPT")
        self.assertEqual(report["observed_fee_class"], "NO_RECEIPT")


if __name__ == "__main__":
    unittest.main()
