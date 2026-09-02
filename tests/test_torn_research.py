import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import torn_research as tr


class TornResearchTests(unittest.TestCase):
    def test_redact_url_hides_common_credentials(self):
        redacted = tr.redact_url("https://example.test/x?key=abc&foo=bar&token=secret")
        self.assertNotIn("abc", redacted)
        self.assertNotIn("secret", redacted)
        self.assertIn("foo=bar", redacted)

    def test_timestamp_inventory_detects_duplicates_and_deltas(self):
        result = tr.timestamp_inventory([
            {"timestamp": 100, "price": 1}, {"timestamp": 160, "price": 1},
            {"timestamp": 160, "price": 1}, {"timestamp": 280, "price": 2},
        ])
        self.assertEqual(result["history_rows"], 4)
        self.assertEqual(result["unique_timestamps"], 3)
        self.assertEqual(result["duplicates"], 1)
        self.assertEqual(result["min_delta_s"], 60)
        self.assertEqual(result["max_delta_s"], 120)
        self.assertEqual(result["pct_60s_delta"], 50.0)

    def test_parse_tornsy_minute_rows_preserves_repeated_prices(self):
        rows = tr.parse_tornsy_rows({"data": [[60, "10.00", 100], [120, "10.00", 101], [180, "10.10", 102]]}, "m1")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["price"], 10.0)
        self.assertEqual(rows[1]["price"], 10.0)

    def test_parse_tornsy_ohlc_rows(self):
        rows = tr.parse_tornsy_rows({"data": [[3600, "10", "12", "9", "11", 1000]]}, "h1")
        self.assertEqual(rows[0]["open"], 10.0)
        self.assertEqual(rows[0]["high"], 12.0)
        self.assertEqual(rows[0]["close"], 11.0)

    def test_tornsy_audit_counts_regular_missing_slots(self):
        result = tr.audit_tornsy_rows([{"timestamp": 60}, {"timestamp": 120}, {"timestamp": 300}], "m1")
        self.assertEqual(result["gap_count"], 1)
        self.assertEqual(result["missing_slots_if_regular"], 2)
        self.assertEqual(result["max_delta_s"], 180)

    def test_reconcile_live_payloads_keeps_differences_explicit(self):
        official = {"stocks": [{"id": 1, "acronym": "LSC", "market": {"price": 10.0, "shares": 100}}]}
        tornsy = {"timestamp": 123, "data": [{"stock": "LSC", "price": "10.01", "total_shares": 99}]}
        result = tr.reconcile_live_payloads(official, tornsy)
        self.assertEqual(result["tornsy_timestamp"], 123)
        self.assertAlmostEqual(result["rows"][0]["price_abs_diff"], 0.01)
        self.assertFalse(result["rows"][0]["price_equal_numeric"])
        self.assertEqual(result["rows"][0]["shares_diff"], 1)

    def test_write_json_immutable_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.json"
            tr.write_json_immutable(path, {"a": 1})
            with self.assertRaises(tr.ResearchToolError):
                tr.write_json_immutable(path, {"a": 2})
            self.assertEqual(json.loads(path.read_text()), {"a": 1})

    def test_normalize_symbol_validation(self):
        self.assertEqual(tr.normalize_symbol(" lsc "), "LSC")
        with self.assertRaises(tr.ResearchToolError):
            tr.normalize_symbol("A1")


if __name__ == "__main__":
    unittest.main()
