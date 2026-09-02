import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))

import run_external_sector_screen as sector


class ExternalSectorScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "research" / "external_driver_candidates.json").read_text(encoding="utf-8"))

    def test_sector_first_universe_is_one_starter_safe_batch(self):
        symbols = sector.sector_request_symbols(self.manifest)
        self.assertEqual(len(symbols), 34)
        self.assertEqual(len(symbols), len(set(symbols)))
        for control in ("SPY", "ACWI", "QQQ", "IWM"):
            self.assertIn(control, symbols)

    def test_named_equities_are_removed_but_sector_proxies_remain(self):
        filtered = sector.sector_only_manifest(self.manifest)
        for stock in filtered["stocks"]:
            self.assertEqual(stock["individual_equity_candidates"], [])
            self.assertTrue(stock["sector_or_industry_proxies"])
        symbols = sector.sector_request_symbols(self.manifest)
        self.assertIn("XLF", symbols)
        self.assertIn("CIBR", symbols)
        self.assertIn("JETS", symbols)
        self.assertNotIn("HSBC", symbols)
        self.assertNotIn("PANW", symbols)
        self.assertNotIn("DAL", symbols)


if __name__ == "__main__":
    unittest.main()
