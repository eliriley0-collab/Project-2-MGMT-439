"""Known answers and regression checks for the public dashboard and baseline."""
import json
from pathlib import Path
from unittest import SkipTest, TestCase, main
from unittest.mock import patch

import numpy as np
from streamlit.testing.v1 import AppTest

import engine as e


class Verification(TestCase):
    @classmethod
    def setUpClass(cls):
        if not (e.DATA / "prices.csv").exists():
            raise SkipTest("Exact historical checks require the authorized original snapshot.")
        cls.prices, cls.signal = e.load_data()

    def test_known_answers(self):
        self.assertEqual(e.weight_grid().shape, (10626, 5))
        self.assertTrue(np.allclose(e.weight_grid().sum(axis=1), 1))
        self.assertTrue((e.weight_grid() >= 0).all())
        self.assertAlmostEqual(e.turnover(e.BENCHMARK, e.START), 1)
        self.assertAlmostEqual(e.net_estimate(e.BENCHMARK, e.START, np.full(5, .05), .01), .0395)
        cov = np.outer([.2, .2, .1, .1, .01], [.2, .2, .1, .1, .01])
        self.assertAlmostEqual(e.annual_risk(e.BENCHMARK, cov), .16)
        self.assertAlmostEqual(e.annual_risk(np.array([.5, .5, 0, 0, 0]), cov), .20)

    def test_point_in_time(self):
        original = e.evaluate(self.prices, self.signal)
        altered = self.prices.copy()
        signal = self.signal.copy()
        altered.iloc[-1] *= 1.5
        signal.iloc[-1] *= .5
        self.assertEqual(original["decisions"], e.evaluate(altered, signal)["decisions"])
        for decision in original["decisions"]:
            asof, date = decision["asof"], decision["date"]
            self.assertLess(asof, date)
            known = self.signal.loc[:asof]
            self.assertAlmostEqual(decision["spy_signal"], known.iloc[-1] / known.iloc[-7] - 1)
        self.assertNotEqual(original["path"], e.evaluate(altered, signal)["path"])
        returns = self.prices.pct_change(fill_method=None).iloc[1:]
        cutoff = original["decisions"][0]["asof"]
        plain, covariance, _ = e.estimates(returns, self.signal, cutoff, e.Settings())
        signal.loc[cutoff] *= .5
        penalized, unchanged, momentum = e.estimates(returns, signal, cutoff, e.Settings())
        self.assertLess(momentum, 0)
        np.testing.assert_allclose(penalized - plain, [-.02, -.02, 0, 0, 0])
        np.testing.assert_array_equal(covariance, unchanged)

    def test_baseline_checks_and_nav(self):
        result = e.evaluate(self.prices, self.signal)
        saved = json.loads(Path("visible-output.json").read_text())
        self.assertEqual(saved, result)
        for record in result["decisions"]:
            best = record["portfolios"][e.NAMES[2]]
            self.assertEqual(best["status"], "Pass")
            self.assertTrue(all(rule["pass"] for rule in best["checks"]))
            self.assertGreaterEqual(best["estimated_net"], .05)
            self.assertLessEqual(best["estimated_volatility"], record["benchmark_risk"])
            self.assertAlmostEqual(best["sp500_weight"], best["weights"]["SPY"] + best["weights"]["VOO"])
            self.assertEqual(record["portfolios"][e.NAMES[-1]]["weights"], dict(zip(e.TICKERS, e.BENCHMARK)))
        date = result["path"][1]["date"]
        equal = result["decisions"][0]["portfolios"][e.NAMES[0]]
        realized = self.prices.loc[date] / self.prices.loc[result["path"][0]["date"]] - 1
        expected = e.INITIAL_VALUE * (1 - equal["cost_fraction"]) * (1 + realized.mean())
        self.assertAlmostEqual(result["path"][1][e.NAMES[0]], expected)

    def test_failure_and_stress_controls(self):
        failed = e.evaluate(self.prices, self.signal, e.Settings(risk_multiple=0))
        statuses = [row["portfolios"][e.NAMES[2]]["status"] for row in failed["decisions"]]
        self.assertEqual(statuses, ["Mandate infeasible", "Stopped after prior failure"])
        self.assertNotIn("weights", failed["decisions"][0]["portfolios"][e.NAMES[2]])
        self.assertTrue(e.performance(failed)[0].empty)
        expensive = e.evaluate(self.prices, self.signal, e.Settings(costs_bps=100))
        initial = expensive["decisions"][0]["portfolios"][e.NAMES[0]]
        self.assertAlmostEqual(initial["cost_usd"], 800)
        app = AppTest.from_file("app.py").run(timeout=15)
        self.assertFalse(app.exception)
        self.assertEqual(app.radio[0].value, "Saved historical results")
        app.radio[0].set_value("Interactive local historical analysis").run(timeout=15)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "Pass")
        self.assertEqual(app.metric[2].value, "5.53%")
        app.selectbox[0].set_value("2024-10-31").run(timeout=15)
        self.assertEqual(app.metric[2].value, "5.23%")
        app.slider[-1].set_value(0)
        app.button[0].click().run(timeout=15)
        self.assertFalse(app.exception)
        self.assertIn("infeasible", app.error[0].value)


class PublicCheckoutVerification(TestCase):
    def test_saved_dashboard_without_vendor_inputs(self):
        with patch.object(e, "DATA", Path("/nonexistent-fin439-snapshot")), patch(
            "engine.evaluate", side_effect=AssertionError("Saved mode must not run the engine.")
        ):
            app = AppTest.from_file("app.py").run(timeout=15)
            self.assertFalse(app.exception)
            self.assertEqual(app.radio[0].value, "Saved historical results")
            self.assertNotIn("Interactive local historical analysis", app.radio[0].options)
            self.assertFalse(app.warning)
            self.assertFalse(app.slider)
            self.assertEqual(list(app.table[0].value["VOO"]), ["20.00%", "5.00%"])
            self.assertEqual(list(app.table[0].value["BIL"]), ["80.00%", "95.00%"])
            metrics = next(frame.value for frame in app.dataframe if "Annualized net" in frame.value)
            self.assertEqual(f'{metrics.loc[e.NAMES[2], "Annualized net"]:.2%}', "5.98%")
            self.assertEqual(f'{metrics.loc[e.NAMES[2], "Realized vol."]:.2%}', "1.91%")
            self.assertEqual(f'{metrics.loc[e.NAMES[-1], "Annualized net"]:.2%}', "11.42%")
            self.assertEqual(f'{metrics.loc[e.NAMES[-1], "Realized vol."]:.2%}', "8.24%")
            self.assertIn("4.30%", app.error[0].value)
            self.assertEqual(list(app.table[1].value["Status"]),
                             ["Mandate infeasible", "Stopped after prior failure"])

    def test_demo_without_vendor_inputs(self):
        with patch.object(e, "DATA", Path("/nonexistent-fin439-snapshot")):
            data = e.load_data(allow_demo=True)
            result = e.evaluate(*data)
            self.assertIn("Synthetic demo", result["data_source"])
            self.assertEqual(result["committee_decision"], e.PILOT_DECISION)
            self.assertEqual(len(result["decisions"]), 2)
            app = AppTest.from_file("app.py").run(timeout=15)
            self.assertFalse(app.exception)
            app.radio[0].set_value("Interactive synthetic demo").run(timeout=15)
            self.assertFalse(app.exception)
            self.assertIn("Synthetic demo", app.warning[0].value)
            selected = result["decisions"][-1]["portfolios"][e.NAMES[2]]
            self.assertEqual(app.metric[2].value, f'{selected["estimated_net"]:.2%}')
            self.assertIn("Stress comparison", [tab.label for tab in app.tabs])
            self.assertIn("0% real capital", app.info[0].value)
            self.assertIn("does not authorize live trading", app.info[0].value)


if __name__ == "__main__":
    main(verbosity=2)
