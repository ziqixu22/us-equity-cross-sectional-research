import unittest

import numpy as np
import pandas as pd

from us_equity_cross_sectional.features.fundamental import (
    compute_fundamental_factors,
    summarize_factor_coverage,
)


def _row(research_date, security_id="AAA", **overrides):
    base = {
        "research_date": pd.Timestamp(research_date),
        "security_id": security_id,
        "market_cap": 2000.0,
        "market_cap_eligible": True,
        "stockholders_equity": 500.0,
        "net_income_ttm": 100.0,
        "revenue_ttm": 1000.0,
        "assets": 1500.0,
        "liabilities": 900.0,
        "gross_profit_ttm": 400.0,
        "operating_income_ttm": 150.0,
    }
    base.update(overrides)
    return base


def _panel(*rows):
    return pd.DataFrame(list(rows))


class FundamentalFactorTest(unittest.TestCase):
    def test_book_to_market_formula(self):
        panel = _panel(_row("2024-06-07", stockholders_equity=500.0, market_cap=2000.0))
        out = compute_fundamental_factors(panel)
        self.assertAlmostEqual(0.25, out.loc[0, "book_to_market"])

    def test_earnings_yield_with_valid_market_cap(self):
        panel = _panel(_row("2024-06-07", net_income_ttm=100.0, market_cap=2000.0))
        out = compute_fundamental_factors(panel)
        self.assertAlmostEqual(0.05, out.loc[0, "earnings_yield"])

    def test_market_cap_dependent_factor_missing_when_ineligible(self):
        panel = _panel(_row("2024-06-07", market_cap_eligible=False, market_cap=2000.0))
        out = compute_fundamental_factors(panel)
        self.assertTrue(pd.isna(out.loc[0, "book_to_market"]))
        self.assertTrue(pd.isna(out.loc[0, "earnings_yield"]))
        self.assertTrue(pd.isna(out.loc[0, "sales_to_price"]))

    def test_roa_uses_average_assets(self):
        panel = _panel(
            _row("2023-06-09", assets=100.0),
            _row("2024-06-07", assets=200.0, net_income_ttm=30.0),
        )
        out = compute_fundamental_factors(panel)
        self.assertAlmostEqual(150.0, out.loc[1, "average_assets"])
        self.assertAlmostEqual(0.2, out.loc[1, "roa"])

    def test_roa_missing_when_prior_year_assets_unavailable(self):
        panel = _panel(_row("2024-06-07", assets=200.0, net_income_ttm=30.0))
        out = compute_fundamental_factors(panel)
        self.assertTrue(pd.isna(out.loc[0, "assets_prior_year_comparable"]))
        self.assertTrue(pd.isna(out.loc[0, "average_assets"]))
        self.assertTrue(pd.isna(out.loc[0, "roa"]))

    def test_gross_profitability(self):
        panel = _panel(
            _row("2023-06-09", assets=100.0),
            _row("2024-06-07", assets=200.0, gross_profit_ttm=45.0),
        )
        out = compute_fundamental_factors(panel)
        self.assertAlmostEqual(0.3, out.loc[1, "gross_profitability"])

    def test_operating_margin(self):
        panel = _panel(_row("2024-06-07", operating_income_ttm=150.0, revenue_ttm=1000.0))
        out = compute_fundamental_factors(panel)
        self.assertAlmostEqual(0.15, out.loc[0, "operating_margin"])

    def test_leverage(self):
        panel = _panel(_row("2024-06-07", liabilities=900.0, assets=1500.0))
        out = compute_fundamental_factors(panel)
        self.assertAlmostEqual(0.6, out.loc[0, "leverage"])

    def test_asset_growth(self):
        panel = _panel(
            _row("2023-06-09", assets=100.0),
            _row("2024-06-07", assets=125.0),
        )
        out = compute_fundamental_factors(panel)
        self.assertAlmostEqual(0.25, out.loc[1, "asset_growth"])

    def test_zero_denominator_is_missing_not_inf(self):
        panel = _panel(
            _row("2024-06-07", market_cap=0.0, net_income_ttm=100.0),
        )
        out = compute_fundamental_factors(panel)
        self.assertTrue(pd.isna(out.loc[0, "earnings_yield"]))
        panel2 = _panel(_row("2024-06-07", assets=0.0, liabilities=900.0))
        out2 = compute_fundamental_factors(panel2)
        self.assertTrue(pd.isna(out2.loc[0, "leverage"]))
        panel3 = _panel(
            _row("2023-06-09", assets=0.0),
            _row("2024-06-07", assets=125.0),
        )
        out3 = compute_fundamental_factors(panel3)
        self.assertTrue(pd.isna(out3.loc[1, "asset_growth"]))

    def test_non_finite_inputs_are_missing(self):
        panel = _panel(_row("2024-06-07", market_cap=float("nan"), net_income_ttm=100.0))
        out = compute_fundamental_factors(panel)
        self.assertTrue(pd.isna(out.loc[0, "earnings_yield"]))
        panel2 = _panel(_row("2024-06-07", net_income_ttm=float("inf"), market_cap=2000.0))
        out2 = compute_fundamental_factors(panel2)
        self.assertTrue(pd.isna(out2.loc[0, "earnings_yield"]))

    def test_sign_is_preserved_for_a_loss(self):
        panel = _panel(_row("2024-06-07", net_income_ttm=-50.0, market_cap=2000.0))
        out = compute_fundamental_factors(panel)
        self.assertAlmostEqual(-0.025, out.loc[0, "earnings_yield"])

    def test_no_future_observation_used_for_prior_year_match(self):
        # Rows deliberately out of chronological order in the input frame,
        # plus an irregular (non-52-week) gap, to prove the match is by
        # calendar date rather than row position or a fixed lookback.
        panel = _panel(
            _row("2024-06-07", "AAA", assets=200.0, net_income_ttm=30.0),
            _row("2022-01-07", "AAA", assets=50.0),
            _row("2023-06-09", "AAA", assets=100.0),
            # A same-security row shortly after the 2024 signal must never
            # be selected as its "prior" value even though it exists.
            _row("2024-06-14", "AAA", assets=999.0),
        )
        out = compute_fundamental_factors(panel).set_index(panel.index)
        row_2024 = out.loc[panel["research_date"].eq(pd.Timestamp("2024-06-07"))].iloc[0]
        self.assertAlmostEqual(100.0, row_2024["assets_prior_year_comparable"])
        self.assertAlmostEqual(150.0, row_2024["average_assets"])
        self.assertAlmostEqual(0.2, row_2024["roa"])

        # The earliest row (2022) has no eligible prior at all: the nearby
        # 2023 row is *after* it, not before, so it must not be borrowed.
        row_2022 = out.loc[panel["research_date"].eq(pd.Timestamp("2022-01-07"))].iloc[0]
        self.assertTrue(pd.isna(row_2022["assets_prior_year_comparable"]))

    def test_summarize_factor_coverage(self):
        panel = _panel(
            _row("2024-06-07", "AAA", market_cap_eligible=True),
            _row("2024-06-07", "BBB", market_cap_eligible=False),
        )
        factors = compute_fundamental_factors(panel)
        summary = summarize_factor_coverage(factors, ("book_to_market",))
        self.assertEqual(1, len(summary))
        self.assertEqual(2, summary.loc[0, "total_observations"])
        self.assertEqual(1, summary.loc[0, "valid_observations"])
        self.assertAlmostEqual(50.0, summary.loc[0, "coverage_pct"])
        self.assertAlmostEqual(50.0, summary.loc[0, "missing_pct"])


if __name__ == "__main__":
    unittest.main()
