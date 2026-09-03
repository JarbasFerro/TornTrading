import json, sys, tempfile, unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
import run_hyp001_prospective as hyp


def ts(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def rows_for_days(start: date, count: int, growth: float = 1.001):
    rows=[]; price=100.0
    for i in range(count):
        day=start.fromordinal(start.toordinal()+i)
        rows.append({"timestamp": ts(day), "open": price, "high": price, "low": price, "close": price, "total_shares": 1})
        price *= growth
    return rows


class Hyp001ProspectiveTests(unittest.TestCase):
    def test_anchor_must_be_prospective_thursday(self):
        hyp.validate_anchor(date(2026, 9, 10))
        with self.assertRaises(hyp.ResearchToolError): hyp.validate_anchor(date(2026, 9, 3))
        with self.assertRaises(hyp.ResearchToolError): hyp.validate_anchor(date(2026, 9, 9))

    def test_capture_window_is_strict_and_timezone_aware(self):
        anchor=date(2026,9,10); anchor_dt=hyp.anchor_datetime(anchor)
        hyp.validate_capture_window(anchor, anchor_dt + timedelta(minutes=15))
        hyp.validate_capture_window(anchor, anchor_dt + timedelta(seconds=hyp.MAX_CAPTURE_DELAY_SECONDS))
        with self.assertRaises(hyp.ResearchToolError): hyp.validate_capture_window(anchor, anchor_dt - timedelta(seconds=1))
        with self.assertRaises(hyp.ResearchToolError): hyp.validate_capture_window(anchor, anchor_dt + timedelta(seconds=hyp.MAX_CAPTURE_DELAY_SECONDS+1))
        with self.assertRaises(hyp.ResearchToolError): hyp.validate_capture_window(anchor, datetime(2026,9,10,0,15))

    def test_percentile_is_linear_and_deterministic(self):
        self.assertAlmostEqual(hyp.percentile([0, 10], .10), 1.0)

    def test_current_forming_daily_open_is_valid_anchor_price(self):
        anchor=date(2026,9,10); a=ts(anchor)
        rows=[{"timestamp": a, "open": 123.45, "close": 999.0}]
        self.assertEqual(hyp.daily_open_map(rows, a)[a], 123.45)

    def test_classification_uses_exact_open_to_open_7d_returns(self):
        anchor=date(2026,9,10); start=date(2025,8,20)
        rows=rows_for_days(start, 390)
        result=hyp.classify_stock(rows, ts(anchor))
        self.assertTrue(result["eligible"])
        self.assertGreaterEqual(result["trailing_return_count"], hyp.MIN_TRAILING_RETURNS)
        self.assertIn("anchor_open", result)
        self.assertIn("prior_7d_return", result)

    def test_insufficient_history_retains_anchor_price_for_prior_outcome(self):
        anchor=date(2026,9,10); start=date(2026,1,1)
        rows=rows_for_days(start, (anchor-start).days+1)
        result=hyp.classify_stock(rows, ts(anchor))
        self.assertFalse(result["eligible"])
        self.assertEqual(result["reason"], "insufficient_trailing_returns")
        self.assertIn("anchor_open", result)

    def test_outcome_does_not_require_new_cohort_eligibility(self):
        previous={"anchor_utc":"2026-09-10T00:00:00Z","stocks":{"ABC":{"eligible":True,"anchor_open":100.0,"condition_met":True}}}
        current={"ABC":{"eligible":False,"reason":"insufficient_trailing_returns","anchor_open":110.0}}
        outcome=hyp.create_outcome(previous,current,"2026-09-17T00:00:00Z")
        self.assertTrue(outcome["stocks"]["ABC"]["eligible"])
        self.assertAlmostEqual(outcome["stocks"]["ABC"]["forward_7d_return"], .10)

    def test_missing_anchor_is_collection_quality_failure_reason(self):
        anchor=date(2026,9,10); start=date(2025,8,20)
        rows=[r for r in rows_for_days(start,390) if r["timestamp"] != ts(anchor)]
        result=hyp.classify_stock(rows,ts(anchor))
        self.assertFalse(result["eligible"]); self.assertEqual(result["reason"],"missing_anchor_open")

    def test_immutable_writer_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"x.json"; hyp.write_immutable(path,{"a":1})
            with self.assertRaises(hyp.ResearchToolError): hyp.write_immutable(path,{"a":2})

    def test_frozen_universe_is_35(self):
        symbols=hyp.load_symbols(ROOT/"research"/"external_driver_candidates.json")
        self.assertEqual(len(symbols),35); self.assertNotIn("TCSE",symbols)

    def test_workflow_enforces_append_only_root_staging_rebase_and_test_order(self):
        text=(ROOT/".github"/"workflows"/"hyp001-prospective.yml").read_text(encoding="utf-8")
        self.assertIn("git add -- research/prospective/HYP-001", text)
        self.assertIn('if [[ "$status" != "A" ]]', text)
        self.assertIn("git rebase origin/main", text)
        self.assertNotIn("git add -- research/prospective/HYP-001/cohorts research/prospective/HYP-001/outcomes", text)
        self.assertLess(text.index("Synchronize with latest main"), text.index("Run unit tests"))


if __name__ == "__main__": unittest.main()
