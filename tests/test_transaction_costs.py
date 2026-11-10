import unittest

import pandas as pd

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_transaction_costs import apply_costs  # noqa: E402
from us_equity_cross_sectional.portfolio.long_short import build_weekly_long_short_returns


class TransactionCostTest(unittest.TestCase):
    def _returns(self):
        return pd.DataFrame({
            "research_date": pd.date_range("2022-01-07", periods=5, freq="W-FRI"),
            "portfolio_return": [0.02, 0.01, -0.01, 0.03, 0.00],
            "turnover": [float("nan"), 0.2, 0.4, 0.1, 0.3],
            "gross_exposure": [2.0] * 5,
        })

    def test_zero_cost_leaves_net_return_equal_to_gross(self):
        out = apply_costs(self._returns(), 0)
        pd.testing.assert_series_equal(
            out["net_return"].reset_index(drop=True),
            out["portfolio_return"].reset_index(drop=True),
            check_names=False,
        )

    def test_first_undefined_turnover_row_is_dropped(self):
        out = apply_costs(self._returns(), 10)
        self.assertEqual(4, len(out))
        self.assertFalse(out["turnover"].isna().any())

    def test_higher_cost_reduces_net_return_monotonically(self):
        base = self._returns()
        net_at = {}
        for bps in (0, 5, 10, 20, 50):
            out = apply_costs(base, bps)
            net_at[bps] = out["net_return"].sum()
        costs = sorted(net_at)
        for a, b in zip(costs, costs[1:]):
            self.assertGreaterEqual(net_at[a], net_at[b])

    def test_trading_cost_matches_turnover_times_exposure_times_rate(self):
        out = apply_costs(self._returns(), 10)
        row = out.iloc[0]
        expected_cost = row["turnover"] * row["gross_exposure"] * (10 / 10_000)
        self.assertAlmostEqual(expected_cost, row["trading_cost"], places=10)
        self.assertAlmostEqual(row["portfolio_return"] - expected_cost, row["net_return"], places=10)

    def test_signed_trading_includes_drift_entry_and_liquidation(self):
        first = pd.Timestamp("2024-01-05")
        second = pd.Timestamp("2024-01-12")
        frame = pd.DataFrame({
            "research_date": [first] * 3 + [second] * 3,
            "security_id": ["short", "middle", "long"] * 2,
            "prediction": [0, 1, 2] * 2,
            "holding_return": [0, 0, 0.1, 0, 0, 0],
            "execution_date": pd.to_datetime(["2024-01-08"] * 3 + ["2024-01-16"] * 3),
            "holding_end_date": pd.to_datetime(["2024-01-16"] * 3 + ["2024-01-22"] * 3),
        })
        returns = build_weekly_long_short_returns(frame, frame, return_column="holding_return", track_trades=True)
        costed = apply_costs(returns, 10)
        self.assertEqual(2, len(costed))
        self.assertAlmostEqual(2.0, returns.loc[0, "traded_notional"])
        self.assertAlmostEqual(2.0 + 1 - 1 / 1.1, returns.loc[1, "traded_notional"])
        self.assertAlmostEqual(0.002, costed.loc[0, "trading_cost"])



if __name__ == "__main__":
    unittest.main()
