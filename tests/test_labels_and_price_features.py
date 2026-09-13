import unittest

import numpy as np
import pandas as pd

from us_equity_cross_sectional.features.labels import (
    add_forward_return_labels,
    add_relative_return_labels,
    validate_weekly_panel_keys,
)
from us_equity_cross_sectional.features.liquidity import add_liquidity, add_split_consistent_volume
from us_equity_cross_sectional.features.momentum import add_momentum
from us_equity_cross_sectional.features.reversal import add_reversal
from us_equity_cross_sectional.features.volatility import add_volatility


def bars(symbol: str, dates: pd.DatetimeIndex, prices: list[float], volume: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": symbol,
            "date": dates,
            "close": prices,
            "adjusted_close": prices,
            "volume": volume,
            "stock_splits": 0.0,
        }
    )


class ForwardReturnLabelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dates = pd.bdate_range("2024-01-02", periods=22)
        self.prices = [100, 102, 103, 105, 104, 108, 110] + list(range(111, 125)) + [130]
        self.frame = bars("AAA", self.dates, self.prices)

    def test_matches_hand_calculated_1d_5d_and_20d_returns(self) -> None:
        labelled = add_forward_return_labels(self.frame, horizons=(1, 5, 20))
        row = labelled.iloc[0]
        self.assertAlmostEqual(103 / 102 - 1, row.forward_return_1d)
        self.assertAlmostEqual(110 / 102 - 1, row.forward_return_5d)
        self.assertAlmostEqual(130 / 102 - 1, row.forward_return_20d)

    def test_uses_next_observed_trading_session_not_calendar_day(self) -> None:
        dates = pd.to_datetime(["2024-01-12", "2024-01-16", "2024-01-17"])
        labelled = add_forward_return_labels(bars("AAA", dates, [100, 102, 103]), horizons=(1,))
        self.assertEqual(pd.Timestamp("2024-01-16"), labelled.iloc[0].execution_date)
        self.assertAlmostEqual(103 / 102 - 1, labelled.iloc[0].forward_return_1d)

    def test_marks_insufficient_future_history_missing(self) -> None:
        labelled = add_forward_return_labels(self.frame, horizons=(20,))
        self.assertTrue(pd.isna(labelled.iloc[1].forward_return_20d))

    def test_keeps_securities_with_different_history_lengths_separate(self) -> None:
        short = bars("BBB", self.dates[5:], self.prices[5:])
        labelled = add_forward_return_labels(pd.concat([self.frame, short]), horizons=(5,))
        self.assertTrue(pd.isna(labelled.loc[labelled.symbol.eq("BBB")].iloc[-1].forward_return_5d))
        self.assertAlmostEqual(110 / 102 - 1, labelled.loc[labelled.symbol.eq("AAA")].iloc[0].forward_return_5d)

    def test_uses_adjusted_close_for_corporate_action_safe_return(self) -> None:
        split = bars("AAA", self.dates[:3], [100, 50, 55])
        split["adjusted_close"] = [50, 50, 55]
        split.loc[1, "stock_splits"] = 2.0
        labelled = add_forward_return_labels(split, horizons=(1,))
        self.assertAlmostEqual(55 / 50 - 1, labelled.iloc[0].forward_return_1d)

    def test_relative_return_uses_equal_weight_mean(self) -> None:
        panel = pd.DataFrame(
            {"research_date": [pd.Timestamp("2024-01-05")] * 2, "forward_return_1d": [0.10, 0.02]}
        )
        relative = add_relative_return_labels(panel, horizons=(1,))
        self.assertAlmostEqual(0.04, relative.iloc[0].relative_return_1d)
        self.assertAlmostEqual(-0.04, relative.iloc[1].relative_return_1d)

    def test_rejects_duplicate_weekly_security_key(self) -> None:
        panel = pd.DataFrame(
            {"research_date": [pd.Timestamp("2024-01-05")] * 2, "security_id": ["yf:AAA"] * 2}
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_weekly_panel_keys(panel)


class PriceFeatureTest(unittest.TestCase):
    def test_split_consistent_volume_restores_comparable_dollar_volume(self) -> None:
        frame = bars("AAA", pd.bdate_range("2024-01-02", periods=3), [25, 25, 26], volume=100.0)
        frame.loc[1:, "volume"] = 400.0
        frame.loc[1, "stock_splits"] = 4.0
        result = add_split_consistent_volume(frame)
        self.assertEqual(4.0, result.iloc[0].split_volume_factor)
        self.assertEqual(1.0, result.iloc[1].split_volume_factor)
        self.assertAlmostEqual(25 * 100 * 4, result.iloc[0].split_consistent_dollar_volume)
        self.assertAlmostEqual(25 * 400, result.iloc[1].split_consistent_dollar_volume)

    def test_momentum_lookback_and_skip_are_exact(self) -> None:
        dates = pd.bdate_range("2022-01-03", periods=253)
        frame = bars("AAA", dates, list(range(100, 353)))
        result = add_momentum(frame)
        row = result.iloc[252]
        self.assertAlmostEqual(331 / 100 - 1, row.momentum_12_1)
        self.assertAlmostEqual(331 / 226 - 1, row.momentum_6_1)
        self.assertAlmostEqual(331 / 289 - 1, row.momentum_3_1)
        self.assertTrue(pd.isna(result.iloc[251].momentum_12_1))

    def test_reversal_has_registered_negative_prior_return_sign(self) -> None:
        frame = bars("AAA", pd.bdate_range("2024-01-02", periods=6), [100, 110, 100, 105, 105, 115])
        result = add_reversal(frame)
        self.assertAlmostEqual(115 / 105 - 1, result.iloc[-1].prior_return_1d)
        self.assertAlmostEqual(-(115 / 105 - 1), result.iloc[-1].reversal_1d)

    def test_volatility_window_ends_at_signal_date_and_downside_uses_negative_returns(self) -> None:
        prices = [100] + [110, 99, 108, 97, 106, 95, 104, 94, 103, 93, 102, 92, 101, 91, 100, 90, 99, 89, 98, 88]
        frame = bars("AAA", pd.bdate_range("2024-01-02", periods=len(prices)), prices)
        result = add_volatility(frame, windows=(20,))
        returns = pd.Series(prices, dtype=float).pct_change(fill_method=None).iloc[1:]
        self.assertAlmostEqual(returns.std(ddof=1) * np.sqrt(252), result.iloc[-1].realized_vol_20d)
        self.assertAlmostEqual(np.sqrt(np.mean(np.minimum(returns, 0) ** 2)) * np.sqrt(252), result.iloc[-1].downside_vol_20d)

    def test_future_price_does_not_change_prior_return_at_signal(self) -> None:
        frame = bars("AAA", pd.bdate_range("2024-01-02", periods=4), [100, 110, 121, 1000])
        result = add_reversal(frame)
        self.assertAlmostEqual(121 / 110 - 1, result.iloc[2].prior_return_1d)

    def test_adv_and_amihud_are_safe_with_zero_volume_and_split_days(self) -> None:
        dates = pd.bdate_range("2024-01-02", periods=21)
        frame = bars("AAA", dates, list(range(100, 121)), volume=100.0)
        frame.loc[0, "volume"] = 0.0
        frame.loc[1, "stock_splits"] = 2.0
        result = add_liquidity(frame, windows=(20,))
        self.assertAlmostEqual(np.mean(np.array(list(range(101, 121))) * 100), result.iloc[-1].adv_20d)
        self.assertTrue(pd.isna(result.iloc[-1].amihud_20d))


if __name__ == "__main__":
    unittest.main()
