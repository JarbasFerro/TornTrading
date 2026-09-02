import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))

import run_publication_boundary_probe as probe


class PublicationBoundaryProbeTests(unittest.TestCase):
    def test_price_maps_exclude_tcse_from_official_targets(self):
        official = {
            "stocks": [
                {"id": 1, "acronym": "AAA", "market": {"price": 10.0}},
                {"id": 2, "acronym": "BBB", "market": {"price": 20.0}},
            ]
        }
        tornsy = {
            "timestamp": 1200,
            "data": [
                {"stock": "AAA", "price": 10.0},
                {"stock": "BBB", "price": 20.0},
                {"stock": "TCSE", "price": 999.0},
            ],
        }
        self.assertEqual(probe.official_price_map(official), {"AAA": 10.0, "BBB": 20.0})
        self.assertEqual(probe.tornsy_price_map(tornsy)["TCSE"], 999.0)

    def test_history_targets_select_exact_boundary(self):
        histories = {
            "AAA": {"stocks": {"chart": {"history": [
                {"timestamp": 1140, "price": 9.0},
                {"timestamp": 1200, "price": 10.0},
            ]}}},
            "BBB": {"stocks": {"chart": {"history": [
                {"timestamp": 1200, "price": 20.0},
            ]}}},
        }
        self.assertEqual(probe.history_targets(histories, 1200), {"AAA": 10.0, "BBB": 20.0})

    def test_analyze_boundary_finds_first_full_matches(self):
        boundary = 1200
        histories = {
            "AAA": {"stocks": {"chart": {"history": [{"timestamp": 1200, "price": 10.0}]}}},
            "BBB": {"stocks": {"chart": {"history": [{"timestamp": 1200, "price": 20.0}]}}},
        }
        samples = [
            {
                "boundary": boundary,
                "server_timestamp": 1199,
                "official_response_received_at_utc": "1970-01-01T00:19:59.500Z",
                "official_prices": {"AAA": 9.0, "BBB": 19.0},
                "tornsy_timestamp": 1140,
                "tornsy_response_received_at_utc": "1970-01-01T00:19:59.600Z",
                "tornsy_prices": {"AAA": 9.0, "BBB": 19.0},
            },
            {
                "boundary": boundary,
                "server_timestamp": 1200,
                "official_response_received_at_utc": "1970-01-01T00:20:00.700Z",
                "official_prices": {"AAA": 10.0, "BBB": 20.0},
                "tornsy_timestamp": 1140,
                "tornsy_response_received_at_utc": "1970-01-01T00:20:00.800Z",
                "tornsy_prices": {"AAA": 9.0, "BBB": 19.0},
            },
            {
                "boundary": boundary,
                "server_timestamp": 1202,
                "official_response_received_at_utc": "1970-01-01T00:20:02.500Z",
                "official_prices": {"AAA": 10.0, "BBB": 20.0},
                "tornsy_timestamp": 1200,
                "tornsy_response_received_at_utc": "1970-01-01T00:20:02.600Z",
                "tornsy_prices": {"AAA": 10.0, "BBB": 20.0},
            },
        ]
        result = probe.analyze_boundary(boundary, samples, histories)
        self.assertEqual(result["history_target_stocks"], 2)
        self.assertEqual(result["first_official_full_match"]["server_timestamp"], 1200)
        self.assertAlmostEqual(result["official_full_match_delay_seconds"], 0.7)
        self.assertEqual(result["first_tornsy_full_match"]["tornsy_timestamp"], 1200)
        self.assertAlmostEqual(result["tornsy_full_match_delay_seconds"], 2.6)
        self.assertAlmostEqual(result["tornsy_minus_official_full_match_delay_seconds"], 1.9)

    def test_choose_first_boundary_skips_too_close_boundary(self):
        self.assertEqual(probe.choose_first_boundary(123.0, 6.0), 180)
        self.assertEqual(probe.choose_first_boundary(175.0, 6.0), 240)


if __name__ == "__main__":
    unittest.main()
