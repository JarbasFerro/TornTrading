import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research" / "external_driver_candidates.json"


class ExternalDriverCandidateUniverseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_has_exact_current_tradable_universe(self):
        rows = self.data["stocks"]
        symbols = [row["torn_symbol"] for row in rows]
        self.assertEqual(len(rows), 35)
        self.assertEqual(len(symbols), len(set(symbols)))
        self.assertNotIn("TCSE", symbols)

    def test_every_stock_has_hypothesis_and_candidates(self):
        valid_confidence = {"HIGH", "MEDIUM", "LOW", "VERY_LOW"}
        for row in self.data["stocks"]:
            self.assertTrue(row["industry_hypothesis"].strip())
            self.assertIn(row["classification_confidence"], valid_confidence)
            self.assertTrue(row["sector_or_industry_proxies"])
            self.assertTrue(row["individual_equity_candidates"])
            self.assertTrue(row["rationale"].strip())

    def test_shared_controls_are_present_and_unique(self):
        controls = [row["symbol"] for row in self.data["shared_controls"]]
        self.assertEqual(len(controls), len(set(controls)))
        for required in ("SPY", "ACWI", "QQQ", "IWM"):
            self.assertIn(required, controls)

    def test_candidate_universe_is_explicitly_hypothesis_only(self):
        self.assertEqual(self.data["research_status"], "HYPOTHESIS_CANDIDATE_UNIVERSE")
        rules = " ".join(self.data["rules"]).lower()
        self.assertIn("not confidence that torn uses", rules)
        self.assertIn("candidate mapping is allowed to fail", rules)
        self.assertIn("observable", rules)


if __name__ == "__main__":
    unittest.main()
