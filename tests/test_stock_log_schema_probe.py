import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import probe_stock_log_schema as probe


class StockLogSchemaProbeTests(unittest.TestCase):
    def test_extracts_current_v2_public_catalog_shapes(self):
        categories_payload = {
            "logcategories": [
                {"id": 10, "title": "Stocks"},
                {"id": 20, "title": "Attacks"},
            ]
        }
        logtypes_payload = {
            "logtypes": [
                {"id": 7, "title": "Stock market: Sell"},
                {"id": 8, "title": "Stock market: Buy"},
            ]
        }
        categories = probe.extract_logcategories(categories_payload)
        self.assertEqual(categories, {10: "Stocks", 20: "Attacks"})
        self.assertEqual(probe.stock_category_ids(categories), [10])
        self.assertEqual(
            probe.extract_logtypes(logtypes_payload),
            {7: "Stock market: Sell", 8: "Stock market: Buy"},
        )

    def test_legacy_mapping_catalog_remains_parseable(self):
        payload = {"logtypes": {"1": "Stock market buy", "2": "Stock market sell"}}
        self.assertEqual(
            probe.extract_logtypes(payload),
            {1: "Stock market buy", 2: "Stock market sell"},
        )

    def test_current_v2_user_log_uses_details_id(self):
        payload = {
            "log": [
                {
                    "id": "private-event-id",
                    "timestamp": 123456789,
                    "details": {"id": 7, "title": "Private rendered title", "category": "Stocks"},
                    "data": {},
                    "params": {},
                }
            ],
            "_metadata": {},
        }
        entries = list(probe.iter_log_entries(payload))
        self.assertEqual(len(entries), 1)
        self.assertEqual(probe.log_type_id(entries[0]), 7)

    def test_schema_summary_discards_values_and_nonpreregistered_private_keys(self):
        declared = {7: "Stock market: Sell"}
        payload = {
            "log": [
                {
                    "id": "secret-event-id",
                    "timestamp": 123456789,
                    "details": {
                        "id": 7,
                        "title": "You sold 999 shares for $123,456",
                        "category": "Stocks",
                    },
                    "data": {
                        "price": 123.45,
                        "shares": 999,
                        "fee": 124,
                        "secret_player_name": "PRIVATE",
                        "ABC": 123456,
                    },
                    "params": {
                        "stock_id": 42,
                        "gross_value": 123456,
                        "private_note": "DO_NOT_PERSIST",
                    },
                }
            ]
        }
        rows = probe.summarize_entries(declared, [payload])
        self.assertEqual(rows[0]["candidate_data_field_types"]["price"], ["float"])
        self.assertEqual(rows[0]["candidate_data_field_types"]["shares"], ["int"])
        self.assertEqual(rows[0]["candidate_data_field_types"]["fee"], ["int"])
        self.assertEqual(rows[0]["candidate_params_field_types"]["stock_id"], ["int"])
        self.assertEqual(rows[0]["candidate_params_field_types"]["gross_value"], ["int"])
        serialized = repr(rows)
        for forbidden in (
            "123.45",
            "123456789",
            "PRIVATE",
            "secret-event-id",
            "DO_NOT_PERSIST",
            "secret_player_name",
            "private_note",
            "ABC",
            "$123,456",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_unknown_log_type_is_ignored(self):
        declared = {7: "Stock market: Sell"}
        payload = {
            "log": [
                {
                    "details": {"id": 999, "title": "Other", "category": "Other"},
                    "data": {"price": 999.99},
                    "params": {},
                }
            ]
        }
        rows = probe.summarize_entries(declared, [payload])
        self.assertEqual(rows[0]["candidate_data_field_types"], {})

    def test_safe_report_rejects_nonpreregistered_private_field_name(self):
        report = {
            "research_status": "SCHEMA_OBSERVATION_ONLY",
            "source": "official_torn_api_v2",
            "retrieved_at_utc": "2026-09-03T04:30:00.000Z",
            "stock_log_type_count": 1,
            "user_log_access": "available",
            "log_types": [
                {
                    "log_type_id": 7,
                    "public_name": "Stock market: Sell",
                    "candidate_data_field_types": {"fee": ["int"]},
                    "candidate_params_field_types": {},
                }
            ],
            "interpretation": "schema only",
        }
        probe.assert_safe_report(report)
        report["log_types"][0]["candidate_data_field_types"]["private_dynamic_key"] = ["string"]
        with self.assertRaises(probe.ResearchToolError):
            probe.assert_safe_report(report)

    def test_safe_report_rejects_unapproved_structure(self):
        report = {
            "research_status": "SCHEMA_OBSERVATION_ONLY",
            "source": "official_torn_api_v2",
            "retrieved_at_utc": "2026-09-03T04:30:00.000Z",
            "stock_log_type_count": 0,
            "user_log_access": "unavailable_or_failed",
            "log_types": [],
            "interpretation": "schema only",
        }
        probe.assert_safe_report(report)
        report["raw_logs"] = []
        with self.assertRaises(probe.ResearchToolError):
            probe.assert_safe_report(report)

    def test_write_report_contains_only_safe_schema(self):
        report = {
            "research_status": "SCHEMA_OBSERVATION_ONLY",
            "source": "official_torn_api_v2",
            "retrieved_at_utc": "2026-09-03T04:30:00.000Z",
            "stock_log_type_count": 0,
            "user_log_access": "unavailable_or_failed",
            "log_types": [],
            "interpretation": "schema only",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            probe.write_report(path, report)
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("api_key", text.lower())
            self.assertNotIn("raw_logs", text.lower())
            self.assertNotIn("observed_count", text.lower())


if __name__ == "__main__":
    unittest.main()
