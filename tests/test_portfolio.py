import unittest

import numpy as np
import pandas as pd

from us_equity_cross_sectional.portfolio.long_short import (
    build_weekly_long_short_returns, portfolio_performance_metrics, cumulative_nav,
)


def _oos_predictions(n_dates=10, n_names=9, seed=0, with_risk=False):
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_dates):
        date = pd.Timestamp("2022-01-07") + pd.Timedelta(weeks=d)
        preds = rng.normal(size=n_names)
        actual = preds * 0.05 + rng.normal(scale=0.001, size=n_names)  # prediction is informative
        for i in range(n_names):
            row = {
                "research_date": date, "security_id": f"S{i}",
                "prediction": preds[i], "forward_return_5d": actual[i],
            }
            if with_risk:
                row["realized_vol_20d"] = abs(rng.normal(loc=0.3, scale=0.05))
            rows.append(row)
    return pd.DataFrame(rows)


class LongShortPortfolioTest(unittest.TestCase):
    def test_equal_weight_long_short_uses_terciles_for_nine_names(self):
        preds = _oos_predictions(n_dates=5, n_names=9)
        returns = build_weekly_long_short_returns(preds, preds, weighting="equal")
        self.assertEqual(5, len(returns))
        self.assertTrue((returns["n_long"] == 3).all())
        self.assertTrue((returns["n_short"] == 3).all())
        self.assertAlmostEqual(2.0, returns["gross_exposure"].iloc[0])

    def test_informative_signal_produces_positive_mean_spread(self):
        preds = _oos_predictions(n_dates=30, n_names=9)
        returns = build_weekly_long_short_returns(preds, preds, weighting="equal")
        self.assertGreater(returns["portfolio_return"].mean(), 0)

    def test_no_sign_flip_for_inverted_signal(self):
        preds = _oos_predictions(n_dates=30, n_names=9)
        preds["prediction"] = -preds["prediction"]
        returns = build_weekly_long_short_returns(preds, preds, weighting="equal")
        self.assertLess(returns["portfolio_return"].mean(), 0)

    def test_inverse_vol_weighting_runs_and_differs_from_equal_weight(self):
        preds = _oos_predictions(n_dates=20, n_names=9)
        panel = _oos_predictions(n_dates=20, n_names=9, with_risk=True)
        equal = build_weekly_long_short_returns(preds, preds, weighting="equal")
        risk_adj = build_weekly_long_short_returns(preds, panel, weighting="inverse_vol")
        self.assertEqual(len(equal), len(risk_adj))
        self.assertFalse(np.allclose(equal["portfolio_return"], risk_adj["portfolio_return"]))

    def test_unknown_weighting_raises(self):
        preds = _oos_predictions(n_dates=5, n_names=9)
        with self.assertRaises(ValueError):
            build_weekly_long_short_returns(preds, preds, weighting="not_a_scheme")

    def test_turnover_is_nan_on_first_date_and_defined_after(self):
        preds = _oos_predictions(n_dates=5, n_names=9)
        returns = build_weekly_long_short_returns(preds, preds, weighting="equal")
        self.assertTrue(pd.isna(returns["turnover"].iloc[0]))
        self.assertFalse(returns["turnover"].iloc[1:].isna().any())

    def test_performance_metrics_on_known_constant_return_series(self):
        returns = pd.DataFrame({
            "research_date": pd.date_range("2022-01-07", periods=52, freq="W-FRI"),
            "portfolio_return": [0.001] * 52,
            "turnover": [0.2] * 52,
            "gross_exposure": [2.0] * 52,
        })
        metrics = portfolio_performance_metrics(returns)
        self.assertEqual(52, metrics["n_periods"])
        self.assertAlmostEqual((1.001 ** 52 - 1), metrics["total_return"], places=6)
        self.assertAlmostEqual(0.0, metrics["annualized_volatility"], places=6)
        self.assertTrue(np.isnan(metrics["sharpe_ratio"]))  # zero vol -> undefined Sharpe
        self.assertAlmostEqual(0.0, metrics["max_drawdown"])
        self.assertAlmostEqual(1.0, metrics["hit_rate"])

    def test_performance_metrics_empty_input(self):
        metrics = portfolio_performance_metrics(pd.DataFrame({"portfolio_return": []}))
        self.assertEqual(0, metrics["n_periods"])

    def test_cumulative_nav_tracks_drawdown(self):
        returns = pd.DataFrame({
            "research_date": pd.date_range("2022-01-07", periods=4, freq="W-FRI"),
            "portfolio_return": [0.10, -0.20, 0.05, 0.05],
        })
        nav = cumulative_nav(returns)
        self.assertAlmostEqual(1.10, nav["nav"].iloc[0])
        self.assertAlmostEqual(1.10 * 0.80, nav["nav"].iloc[1])
        self.assertLess(nav["drawdown"].iloc[1], 0)


if __name__ == "__main__":
    unittest.main()
