import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))

import run_external_named_followup as followup


class ExternalNamedFollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_path = ROOT / "research" / "external_driver_candidates.json"
        cls.plan_path = ROOT / "research" / "external_named_followup_v1.json"

    def test_plan_and_request_set_are_frozen(self):
        source = followup.base.load_manifest(self.source_path)
        plan = followup.load_plan(self.plan_path)
        symbols = followup.named_request_symbols(source, plan)
        self.assertEqual(set(symbols), set(followup.EXPECTED_REQUEST_SYMBOLS))
        self.assertEqual(len(symbols), 10)

    def test_only_tsb_retains_research_candidates(self):
        source = followup.base.load_manifest(self.source_path)
        plan = followup.load_plan(self.plan_path)
        filtered = followup.named_followup_manifest(source, plan)

        self.assertEqual(len(filtered["stocks"]), 35)
        tsb_rows = [row for row in filtered["stocks"] if row["torn_symbol"] == "TSB"]
        self.assertEqual(len(tsb_rows), 1)
        tsb = tsb_rows[0]
        self.assertEqual(tuple(tsb["sector_or_industry_proxies"]), followup.FROZEN_SECTOR_PROXIES)
        self.assertEqual(tuple(tsb["individual_equity_candidates"]), followup.FROZEN_NAMED_CANDIDATES)

        for row in filtered["stocks"]:
            if row["torn_symbol"] == "TSB":
                continue
            self.assertEqual(row["sector_or_industry_proxies"], [])
            self.assertEqual(row["individual_equity_candidates"], [])

    def test_source_manifest_is_not_mutated(self):
        source = followup.base.load_manifest(self.source_path)
        original = json.loads(json.dumps(source))
        plan = followup.load_plan(self.plan_path)
        followup.named_followup_manifest(source, plan)
        self.assertEqual(source, original)

    def test_plan_rejects_candidate_expansion(self):
        original = json.loads(self.plan_path.read_text(encoding="utf-8"))
        original["promoted_stocks"][0]["named_equity_candidates"].append("GS")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaises(followup.ResearchToolError):
                followup.load_plan(path)

    def test_source_candidate_drift_is_rejected(self):
        source = followup.base.load_manifest(self.source_path)
        plan = followup.load_plan(self.plan_path)
        mutated = json.loads(json.dumps(source))
        for row in mutated["stocks"]:
            if row["torn_symbol"] == "TSB":
                row["individual_equity_candidates"].append("GS")
                break
        with self.assertRaises(followup.ResearchToolError):
            followup.named_followup_manifest(mutated, plan)


if __name__ == "__main__":
    unittest.main()
