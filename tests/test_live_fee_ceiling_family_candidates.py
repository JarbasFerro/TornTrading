import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import snapshot_live_fee_ceiling_family_candidates as live


def stock(stock_id, acronym, name, price):
    return {"id": stock_id, "acronym": acronym, "name": name, "market": {"price": price}}


class LiveBroadFeeCandidateTests(unittest.TestCase):
    def test_hrg_272_67_has_broad_candidate(self):
        rows = live.build_candidates([stock(1, "HRG", "Home Retail Group", 272.67)])
        self.assertTrue(rows)
        first = rows[0]
        self.assertEqual(first["stock_acronym"], "HRG")
        self.assertEqual(first["planned_price"], "272.67")
        self.assertEqual(first["shares"], 4)
        self.assertEqual(first["boundary_multiplier"], 1)
        self.assertEqual(first["ceiling_family_fee"], 2)
        self.assertEqual(first["non_ceiling_fee"], 1)
        live.validate_candidate(first)

    def test_subcent_official_price_is_rejected(self):
        with self.assertRaises(ValueError):
            live.official_price(stock(1, "AAA", "A", "272.671"))

    def test_tcse_excluded(self):
        rows = live.build_candidates([
            stock(1, "TCSE", "Index", 272.67),
            stock(2, "HRG", "Home Retail Group", 272.67),
        ])
        self.assertNotIn("TCSE", {row["stock_acronym"] for row in rows})

    def test_report_revalidates_every_candidate(self):
        report = live.build_report(
            [stock(1, "HRG", "Home Retail Group", 272.67), stock(2, "AAA", "A", 100.01)],
            server_timestamp=1788464000,
            retrieved_at_utc="2026-09-03T20:00:00.000Z",
        )
        self.assertEqual(report["research_status"], "LIVE_P0_E5B_CANDIDATE_SNAPSHOT")
        for row in report["candidates"]:
            live.validate_candidate(row)
        self.assertLessEqual(Decimal(report["max_gross"]), Decimal("5000"))


if __name__ == "__main__":
    unittest.main()
