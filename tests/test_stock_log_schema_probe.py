import sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import probe_stock_log_schema as probe


class StockLogSchemaProbeTests(unittest.TestCase):
    def test_extracts_and_filters_public_stock_logtypes(self):
        payload = {"logtypes": {"1": "Stock market buy", "2": "Attack won", "3": "Stocks sold"}}
        all_types = probe.extract_logtypes(payload)
        self.assertEqual(probe.stock_logtypes(all_types), {1: "Stock market buy", 3: "Stocks sold"})

    def test_batches_never_exceed_api_filter_limit(self):
        values = list(range(25))
        batches = list(probe.chunks(values))
        self.assertEqual([len(batch) for batch in batches], [10, 10, 5])
        self.assertTrue(all(len(batch) <= probe.MAX_LOG_FILTERS for batch in batches))

    def test_schema_summary_discards_all_log_values(self):
        declared = {7: "Stock sold"}
        payload = {
            "log": {
                "secret-event-id": {
                    "log": 7,
                    "timestamp": 123456789,
                    "title": "You sold 999 shares for $123,456",
                    "data": {"price": 123.45, "shares": 999, "fee": 124, "secret": "PRIVATE"},
                    "params": {"stock": "ABC", "amount": 123456},
                }
            }
        }
        rows = probe.summarize_entries(declared, [payload])
        self.assertEqual(rows[0]["observed_count"], 1)
        self.assertEqual(rows[0]["data_field_types"]["price"], ["float"])
        serialized = repr(rows)
        for forbidden in ("123.45", "123456789", "PRIVATE", "secret-event-id", "ABC", "$123,456"):
            self.assertNotIn(forbidden, serialized)

    def test_safe_report_rejects_unapproved_structure(self):
        report = {
            "research_status": "SCHEMA_OBSERVATION_ONLY",
            "source": "official_torn_api_v2",
            "stock_log_type_count": 1,
            "observed_stock_log_type_count": 1,
            "user_log_access": "available",
            "log_types": [{
                "log_type_id": 7,
                "public_name": "Stock sold",
                "observed_count": 1,
                "data_field_types": {"fee": ["int"]},
                "params_field_types": {},
            }],
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
            "stock_log_type_count": 0,
            "observed_stock_log_type_count": 0,
            "user_log_access": "unavailable_or_insufficient",
            "log_types": [],
            "interpretation": "schema only",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            probe.write_report(path, report)
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("api_key", text.lower())
            self.assertNotIn("raw", text.lower())


if __name__ == "__main__":
    unittest.main()
