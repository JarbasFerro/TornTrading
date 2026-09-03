import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import run_stock_sell_fee_rounding_diagnostic as runner


class FeeRoundingDiagnosticRunnerTests(unittest.TestCase):
    def test_user_log_query_is_restricted_to_current_documented_keys(self):
        query = {
            "log": "5511",
            "from": 100,
            "to": 200,
            "limit": 100,
            "sort": "DESC",
            "key": "PRIVATE",
            "timestamp": 123,
            "comment": "private",
            "target": 42,
        }
        sanitized = runner.sanitize_query("/user/log", query)
        self.assertEqual(
            sanitized,
            {"log": "5511", "from": 100, "to": 200, "limit": 100},
        )

    def test_non_user_log_query_is_not_rewritten(self):
        query = {"timestamp": 123, "comment": "x"}
        self.assertEqual(runner.sanitize_query("/torn/timestamp", query), query)

    def test_none_query_remains_none(self):
        self.assertIsNone(runner.sanitize_query("/user/log", None))

    def test_documented_key_set_excludes_sort(self):
        self.assertNotIn("sort", runner.DOCUMENTED_USER_LOG_QUERY_KEYS)
        self.assertEqual(
            runner.DOCUMENTED_USER_LOG_QUERY_KEYS,
            frozenset({"log", "from", "to", "limit"}),
        )


if __name__ == "__main__":
    unittest.main()
