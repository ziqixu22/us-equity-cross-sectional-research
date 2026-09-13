import unittest

import numpy as np
import pandas as pd

from us_equity_cross_sectional.research.factor_evaluation import (
    daily_rank_ic,
    summarize_ic,
    quantile_returns,
    quantile_spread,
    alpha_decay,
    yearly_ic_stability,
    factor_coverage,
    factor_persistence,
    evaluate_all_factors,
)


def _perfect_panel(n_dates=10, n_names=6, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_dates):
        date = pd.Timestamp("2023-01-06") + pd.Timedelta(weeks=d)
        factor_vals = rng.normal(size=n_names)
        # label is a monotonic (rank-preserving) function of the factor plus noise
        label_vals = factor_vals + rng.normal(scale=0.001, size=n_names)
        for i in range(n_names):
            rows.append({
                "research_date": date, "security_id": f"S{i}",
                "factor": factor_vals[i], "forward_return_5d": label_vals[i],
                "forward_return_1d": label_vals[i] * 0.2,
                "forward_return_20d": label_vals[i] * 4,
            })
    return pd.DataFrame(rows)


class FactorEvaluationTest(unittest.TestCase):
    def test_daily_rank_ic_perfect_signal_is_near_one(self):
        panel = _perfect_panel()
        ic = daily_rank_ic(panel, "factor", "forward_return_5d")
        self.assertEqual(10, len(ic))
        self.assertGreater(ic["rank_ic"].mean(), 0.9)

    def test_daily_rank_ic_skips_dates_below_min_obs(self):
        panel = _perfect_panel(n_dates=2, n_names=6)
        sparse_date = panel["research_date"].unique()[0]
        panel = panel.loc[~((panel.research_date == sparse_date) & (panel.security_id.isin(["S2", "S3", "S4", "S5"])))]
        ic = daily_rank_ic(panel, "factor", "forward_return_5d", min_obs=3)
        self.assertEqual(1, len(ic))  # the sparse date (2 names left) is skipped

    def test_summarize_ic_matches_manual_computation(self):
        ic_frame = pd.DataFrame({"research_date": range(4), "rank_ic": [0.5, -0.2, 0.3, 0.1]})
        summary = summarize_ic(ic_frame)
        self.assertEqual(4, summary["n_dates"])
        self.assertAlmostEqual(0.175, summary["mean_ic"])
        self.assertAlmostEqual(0.75, summary["pct_positive"])

    def test_summarize_ic_empty_input(self):
        summary = summarize_ic(pd.DataFrame())
        self.assertEqual(0, summary["n_dates"])
        self.assertTrue(pd.isna(summary["mean_ic"]))

    def test_quantile_spread_positive_for_positively_related_factor(self):
        panel = _perfect_panel(n_dates=8, n_names=10)
        spread = quantile_spread(panel, "factor", "forward_return_5d", n_quantiles=5)
        self.assertGreater(spread["n_dates"], 0)
        self.assertGreater(spread["mean_spread"], 0)

    def test_quantile_spread_no_sign_flip_for_inverse_factor(self):
        # A factor that is *negatively* related to the label must show a
        # negative spread -- this module must never flip signs.
        panel = _perfect_panel(n_dates=8, n_names=10)
        panel["inverse_factor"] = -panel["factor"]
        spread = quantile_spread(panel, "inverse_factor", "forward_return_5d", n_quantiles=5)
        self.assertLess(spread["mean_spread"], 0)

    def test_quantile_returns_monotonic_for_strong_signal(self):
        panel = _perfect_panel(n_dates=15, n_names=10)
        result = quantile_returns(panel, "factor", "forward_return_5d", n_quantiles=5)
        result = result.sort_values("quantile")
        means = result["mean"].tolist()
        self.assertEqual(means, sorted(means))

    def test_alpha_decay_reports_all_available_horizons(self):
        panel = _perfect_panel(n_dates=8, n_names=8)
        decay = alpha_decay(panel, "factor")
        self.assertEqual({"1d", "5d", "20d"}, set(decay["horizon"]))
        self.assertTrue((decay["mean_ic"] > 0).all())

    def test_yearly_ic_stability_groups_by_year(self):
        panel = _perfect_panel(n_dates=60, n_names=6)  # spans >1 year at weekly cadence
        stability = yearly_ic_stability(panel, "factor", "forward_return_5d")
        self.assertGreaterEqual(len(stability), 1)
        self.assertIn("year", stability.columns)

    def test_factor_coverage_counts_missing_correctly(self):
        panel = pd.DataFrame({"factor": [1.0, np.nan, 3.0, np.nan]})
        coverage = factor_coverage(panel, "factor")
        self.assertEqual(2, coverage["valid_observations"])
        self.assertEqual(4, coverage["total_observations"])
        self.assertAlmostEqual(50.0, coverage["coverage_pct"])

    def test_factor_persistence_high_for_slow_moving_factor(self):
        # A factor that barely changes week to week should show high rank autocorrelation.
        rng = np.random.default_rng(1)
        base = rng.normal(size=6)
        rows = []
        for d in range(10):
            date = pd.Timestamp("2023-01-06") + pd.Timedelta(weeks=d)
            vals = base + rng.normal(scale=0.01, size=6)
            for i in range(6):
                rows.append({"research_date": date, "security_id": f"S{i}", "factor": vals[i]})
        panel = pd.DataFrame(rows)
        persistence = factor_persistence(panel, "factor")
        self.assertGreater(persistence["mean_rank_autocorr"], 0.9)

    def test_evaluate_all_factors_returns_one_row_per_factor(self):
        panel = _perfect_panel(n_dates=10, n_names=8)
        panel["other_factor"] = -panel["factor"]
        result = evaluate_all_factors(panel, ["factor", "other_factor"], primary_label="forward_return_5d")
        self.assertEqual(2, len(result))
        self.assertIn("ic_5d", result.columns)
        row = result.set_index("factor")
        self.assertGreater(row.loc["factor", "mean_ic"], 0)
        self.assertLess(row.loc["other_factor", "mean_ic"], 0)


if __name__ == "__main__":
    unittest.main()
