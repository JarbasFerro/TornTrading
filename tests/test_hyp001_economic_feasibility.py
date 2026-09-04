import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import run_hyp001_economic_feasibility as econ


class Hyp001EconomicFeasibilityTests(unittest.TestCase):
    def test_ceiling_fee_uses_project_decision_rule(self):
        self.assertEqual(econ.ceiling_fee(Decimal("1000.01")), Decimal("2"))
        self.assertEqual(econ.ceiling_fee(Decimal("2000.00")), Decimal("2"))

    def test_modeled_net_return_applies_symmetric_adverse_stress(self):
        unstressed = econ.modeled_net_return(100.0, 110.0, notional=100_000, stress_bps=0)
        stressed = econ.modeled_net_return(100.0, 110.0, notional=100_000, stress_bps=25)
        self.assertIsNotNone(unstressed)
        self.assertIsNotNone(stressed)
        self.assertGreater(unstressed, stressed)

    def test_notional_too_small_for_one_share_is_unavailable(self):
        self.assertIsNone(econ.modeled_net_return(20_000.0, 21_000.0, notional=10_000, stress_bps=0))

    def test_weekly_spread_is_equal_weight_by_cohort_not_pooled(self):
        rows = [
            {"anchor": "2026-01-01", "condition_met": True, "gross_return": 0.10},
            {"anchor": "2026-01-01", "condition_met": False, "gross_return": 0.00},
            {"anchor": "2026-01-08", "condition_met": True, "gross_return": 0.00},
            {"anchor": "2026-01-08", "condition_met": False, "gross_return": 0.20},
            {"anchor": "2026-01-08", "condition_met": False, "gross_return": 0.20},
            {"anchor": "2026-01-08", "condition_met": False, "gross_return": 0.20},
        ]
        spreads = econ.weekly_spreads(rows, "gross_return")
        self.assertEqual(len(spreads), 2)
        self.assertAlmostEqual(spreads[0], 0.10)
        self.assertAlmostEqual(spreads[1], -0.20)
        self.assertAlmostEqual(sum(spreads) / len(spreads), -0.05)

    def test_cutoff_prevents_post_september_3_outcomes(self):
        anchors = econ.candidate_anchors({
            "AAA": [
                {"timestamp": 1_620_259_200, "open": 10.0},
                {"timestamp": 1_788_393_600, "open": 11.0},
            ]
        })
        self.assertTrue(anchors)
        self.assertLessEqual(anchors[-1] + econ.timedelta(days=7), econ.DISCOVERY_OUTCOME_CUTOFF)

    def test_feasibility_classification_uses_frozen_primary_threshold(self):
        observations = [
            {"condition_met": True} for _ in range(60)
        ] + [{"condition_met": False} for _ in range(60)]
        primary = {"signaled_mean_net": 0.01, "mean_weekly_net_spread": 0.003}
        quartiles = [
            {"primary_mean_weekly_net_spread": 0.001},
            {"primary_mean_weekly_net_spread": 0.001},
            {"primary_mean_weekly_net_spread": 0.001},
            {"primary_mean_weekly_net_spread": -0.001},
        ]
        classification, _ = econ.classify_feasibility(observations, primary, quartiles)
        self.assertEqual(classification, "ECONOMICALLY_PLAUSIBLE")

    def test_negative_primary_net_rejects_economic_plausibility(self):
        observations = [{"condition_met": True} for _ in range(100)]
        primary = {"signaled_mean_net": -0.001, "mean_weekly_net_spread": 0.005}
        quartiles = [{"primary_mean_weekly_net_spread": 0.001}] * 4
        classification, _ = econ.classify_feasibility(observations, primary, quartiles)
        self.assertEqual(classification, "NOT_ECONOMICALLY_PLAUSIBLE")

    def test_summary_schema_rejects_trade_level_injection(self):
        summary = {
            "research_status": "DISCOVERY_SAMPLE_ECONOMIC_FEASIBILITY_NOT_CONFIRMATORY",
            "hypothesis_id": "HYP-001",
            "source": "audited_tornsy_d1",
            "generated_at_utc": "2026-09-04T00:00:00Z",
            "discovery_outcome_cutoff_utc": "2026-09-03T00:00:00Z",
            "universe_size": 35,
            "source_fetches": 35,
            "source_errors": 0,
            "eligible_observations": 0,
            "signaled_observations": 0,
            "non_signaled_observations": 0,
            "cohorts_with_eligible_observations": 0,
            "cohorts_with_cross_sectional_spread": 0,
            "gross_observation_metrics": {key: None for key in econ.GROSS_OBS_KEYS},
            "gross_weekly_cross_sectional_metrics": {key: None for key in econ.GROSS_WEEKLY_KEYS},
            "scenario_metrics": [
                {
                    "notional": n,
                    "stress_bps_per_leg": s,
                    "signaled_available": 0,
                    "non_signaled_available": 0,
                    "signaled_unavailable": 0,
                    "non_signaled_unavailable": 0,
                    "signaled_mean_net": None,
                    "signaled_median_net": None,
                    "non_signaled_mean_net": None,
                    "non_signaled_median_net": None,
                    "signaled_positive_net_rate": None,
                    "mean_weekly_net_spread": None,
                    "median_weekly_net_spread": None,
                    "positive_weekly_net_spread_rate": None,
                    "cohorts_with_net_spread": 0,
                }
                for n in econ.POSITION_NOTIONALS for s in econ.STRESS_BPS
            ],
            "chronological_quartiles": [
                {
                    "quartile": q,
                    "cohort_count": 0,
                    "eligible_observations": 0,
                    "signaled_count": 0,
                    "non_signaled_count": 0,
                    "signaled_mean_gross": None,
                    "non_signaled_mean_gross": None,
                    "mean_weekly_gross_spread": None,
                    "primary_mean_weekly_net_spread": None,
                }
                for q in range(1, 5)
            ],
            "primary_scenario": {},
            "feasibility_classification": "MARGINAL_OR_UNSTABLE",
            "classification_reasons": [],
            "claim_boundary": "x",
            "execution_note": "x",
        }
        econ.assert_safe_summary(summary)
        summary["raw_trade_returns"] = [0.1]
        with self.assertRaises(econ.ResearchToolError):
            econ.assert_safe_summary(summary)


if __name__ == "__main__":
    unittest.main()
