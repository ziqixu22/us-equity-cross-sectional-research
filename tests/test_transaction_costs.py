import unittest

import pandas as pd

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_transaction_costs import apply_costs  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
