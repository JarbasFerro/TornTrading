import sys
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import analyze_stock_sell_fee_rounding as base
import diagnose_stock_sell_fee_rounding as diag


class FakeClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def get(self, path, query=None):
        self.calls.append((path, dict(query or {})))
        if not self.payloads:
            raise AssertionError("unexpected extra API request")
        return SimpleNamespace(payload=self.payloads.pop(0))


def sell_entry(event_id, timestamp, amount=1000, price="1.000", fees=1):
    return {
        "id": event_id,
        "timestamp": timestamp,
        "details": {"id": base.SELL_LOG_TYPE_ID, "title": "Stock sell", "category": "Stocks"},
        "data": {
            "amount": amount,
            "price": price,
            "fees": fees,
            "profit": 987654321,
            "stock": 42,
        },
        "params": {"private_note": "DO_NOT_PERSIST"},
    }


class StockSellFeeRoundingDiagnosticTests(unittest.TestCase):
    def test_safe_next_link_is_reduced_to_frozen_allowlist(self):
        payload = {
            "_metadata": {
                "links": {
                    "next": (
                        "https://api.torn.com/v2/user/log?log=5511&from=100&to=190&sort=DESC&limit=100"
                        "&key=SECRET&foo=PRIVATE"
                    )
                }
            }
        }
        params = diag.next_page_params(payload, window_start=100, window_end=200)
        self.assertEqual(
            params,
            {"log": "5511", "from": 100, "to": 190, "sort": "DESC", "limit": 100},
        )
        self.assertNotIn("key", params)
        self.assertNotIn("foo", params)

    def test_relative_next_link_is_accepted(self):
        payload = {
            "_metadata": {
                "links": {
                    "next": "/v2/user/log?log=5511&from=100&to=190&sort=DESC&limit=100"
                }
            }
        }
        params = diag.next_page_params(payload, window_start=100, window_end=200)
        self.assertEqual(params["to"], 190)

    def test_pagination_rejects_unsafe_or_scope_changing_links(self):
        bad_links = [
            "http://api.torn.com/v2/user/log?log=5511&from=100&to=190&sort=DESC&limit=100",
            "https://evil.example/v2/user/log?log=5511&from=100&to=190&sort=DESC&limit=100",
            "https://api.torn.com/v2/user/stocks?log=5511&from=100&to=190&sort=DESC&limit=100",
            "https://api.torn.com/v2/user/log?log=5510&from=100&to=190&sort=DESC&limit=100",
            "https://api.torn.com/v2/user/log?log=5511&from=99&to=190&sort=DESC&limit=100",
            "https://api.torn.com/v2/user/log?log=5511&from=100&to=201&sort=DESC&limit=100",
            "https://api.torn.com/v2/user/log?log=5511&from=100&to=190&sort=DESC&limit=101",
            "https://api.torn.com/v2/user/log?log=5511&from=100&to=190&sort=ASC&limit=100",
        ]
        for link in bad_links:
            with self.subTest(link=link):
                with self.assertRaises(diag.ResearchToolError):
                    diag.next_page_params(
                        {"_metadata": {"links": {"next": link}}},
                        window_start=100,
                        window_end=200,
                    )

    def test_two_page_collection_deduplicates_and_exhausts(self):
        page1 = {
            "log": [
                sell_entry("event-a", 190),
                sell_entry("event-b", 180),
            ],
            "_metadata": {
                "links": {
                    "next": "https://api.torn.com/v2/user/log?log=5511&from=100&to=180&sort=DESC&limit=100"
                }
            },
        }
        page2 = {
            "log": [
                sell_entry("event-b", 180),
                sell_entry("event-c", 170),
            ],
            "_metadata": {"links": {"next": None, "prev": None}},
        }
        client = FakeClient([page1, page2])
        observations, rejected, duplicates, exhausted, pages = diag.collect_paginated_sales(
            client,
            window_start=100,
            window_end=200,
        )
        self.assertEqual(len(observations), 3)
        self.assertEqual(rejected, 0)
        self.assertEqual(duplicates, 1)
        self.assertTrue(exhausted)
        self.assertEqual(pages, 2)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[1][1]["to"], 180)

    def test_pagination_must_advance_unique_events(self):
        page1 = {
            "log": [sell_entry("event-a", 190)],
            "_metadata": {
                "links": {
                    "next": "https://api.torn.com/v2/user/log?log=5511&from=100&to=190&sort=DESC&limit=100"
                }
            },
        }
        page2 = {
            "log": [sell_entry("event-a", 190)],
            "_metadata": {
                "links": {
                    "next": "https://api.torn.com/v2/user/log?log=5511&from=100&to=189&sort=DESC&limit=100"
                }
            },
        }
        client = FakeClient([page1, page2])
        with self.assertRaises(diag.ResearchToolError):
            diag.collect_paginated_sales(client, window_start=100, window_end=200)

    def test_price_quantum_preserves_logged_trailing_precision(self):
        self.assertEqual(diag.price_quantum(Decimal("12.3400")), Decimal("0.0001"))
        self.assertEqual(diag.price_quantum(Decimal("12")), Decimal("1"))

    def test_one_dollar_ceiling_mismatch_can_be_precision_compatible(self):
        observation = diag.DiagnosticSale(
            sale=base.SaleObservation(amount=1000, price=Decimal("1.000"), fee=2),
            timestamp=190,
            event_id="PRIVATE_EVENT",
            price_quantum=Decimal("0.001"),
        )
        self.assertTrue(diag.precision_interval_reconciles(observation, "nearest_half_quantum"))
        self.assertTrue(diag.precision_interval_reconciles(observation, "downward_truncation_quantum"))

    def test_reference_diagnostic_counts_residuals_and_quartiles(self):
        observations = [
            diag.DiagnosticSale(
                sale=base.SaleObservation(amount=1000, price=Decimal("1.000"), fee=fee_value),
                timestamp=100 + index,
                event_id=f"PRIVATE-{index}",
                price_quantum=Decimal("0.001"),
            )
            for index, fee_value in enumerate([1, 2, 1, 1, 2, 1, 1, 1])
        ]
        result = diag.reference_ceiling_diagnostic(observations)
        self.assertEqual(result["matches"], 6)
        self.assertEqual(result["mismatches"], 2)
        self.assertEqual(sum(result["residual_direction_counts"].values()), 8)
        self.assertEqual(sum(result["absolute_residual_bucket_counts"].values()), 2)
        self.assertEqual(sum(row["observations"] for row in result["chronological_quartiles"]), 8)
        self.assertEqual(sum(row["mismatches"] for row in result["chronological_quartiles"]), 2)

    def test_aggregate_report_does_not_persist_private_trade_values(self):
        observations = [
            diag.DiagnosticSale(
                sale=base.SaleObservation(amount=1234567, price=Decimal("98765.432109"), fee=121932631),
                timestamp=1765432109,
                event_id="SUPER-SECRET-EVENT-ID",
                price_quantum=Decimal("0.000001"),
            )
        ]
        report = diag.build_report(
            observations,
            rejected=0,
            duplicates=0,
            pages=1,
            exhausted=True,
            retrieved_at="2026-09-03T05:30:00.000Z",
        )
        diag.assert_safe_report(report)
        serialized = repr(report)
        for forbidden in (
            "1234567",
            "98765.432109",
            "121932631",
            "1765432109",
            "SUPER-SECRET-EVENT-ID",
            "987654321",
            "DO_NOT_PERSIST",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_safe_report_rejects_raw_transaction_field(self):
        report = diag.build_report(
            [],
            rejected=0,
            duplicates=0,
            pages=0,
            exhausted=True,
            retrieved_at="2026-09-03T05:30:00.000Z",
        )
        report["raw_logs"] = []
        with self.assertRaises(diag.ResearchToolError):
            diag.assert_safe_report(report)


if __name__ == "__main__":
    unittest.main()
