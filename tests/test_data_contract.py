import unittest

import pandas as pd

from us_equity_cross_sectional.data.point_in_time import (
    assert_feature_table_excludes_labels,
    assert_fundamentals_as_filed,
    assert_panel_timing,
    select_latest_as_filed,
)
from us_equity_cross_sectional.data.validation import validate_daily_bars


class DailyBarsValidationTest(unittest.TestCase):
    def test_rejects_duplicate_symbol_date_records(self) -> None:
        bars = pd.DataFrame(
            {
                "symbol": ["ABC", "ABC"],
                "date": pd.to_datetime(["2024-01-02", "2024-01-02"]),
                "open": [10.0, 10.0],
                "high": [11.0, 11.0],
                "low": [9.0, 9.0],
                "close": [10.5, 10.5],
                "volume": [100, 100],
            }
        )

        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_daily_bars(bars)

    def test_rejects_impossible_ohlc_relationship(self) -> None:
        bars = pd.DataFrame(
            {
                "symbol": ["ABC"],
                "date": pd.to_datetime(["2024-01-02"]),
                "open": [10.0],
                "high": [9.0],
                "low": [8.0],
                "close": [10.5],
                "volume": [100],
            }
        )

        with self.assertRaisesRegex(ValueError, "OHLC"):
            validate_daily_bars(bars)


class PointInTimeContractTest(unittest.TestCase):
    def test_rejects_feature_available_after_signal(self) -> None:
        panel = pd.DataFrame(
            {
                "security_id": ["1"],
                "signal_time": pd.to_datetime(["2024-02-15 21:00:00+00:00"]),
                "available_at": pd.to_datetime(["2024-02-16 13:00:00+00:00"]),
                "execution_time": pd.to_datetime(["2024-02-16 21:00:00+00:00"]),
            }
        )

        with self.assertRaisesRegex(ValueError, "available_at"):
            assert_panel_timing(panel)

    def test_rejects_same_close_execution(self) -> None:
        panel = pd.DataFrame(
            {
                "security_id": ["1"],
                "signal_time": pd.to_datetime(["2024-02-15 21:00:00+00:00"]),
                "available_at": pd.to_datetime(["2024-02-15 20:00:00+00:00"]),
                "execution_time": pd.to_datetime(["2024-02-15 21:00:00+00:00"]),
            }
        )

        with self.assertRaisesRegex(ValueError, "execution_time"):
            assert_panel_timing(panel)

    def test_rejects_as_filed_value_not_public_by_signal_time(self) -> None:
        facts = pd.DataFrame(
            {
                "accession_number": ["0001"],
                "available_at": pd.to_datetime(["2024-02-16 00:00:00+00:00"]),
                "signal_time": pd.to_datetime(["2024-02-15 21:00:00+00:00"]),
            }
        )

        with self.assertRaisesRegex(ValueError, "as-filed"):
            assert_fundamentals_as_filed(facts)

    def test_selects_original_then_amended_value_only_after_amendment(self) -> None:
        facts = pd.DataFrame(
            {
                "security_id": ["1", "1"],
                "concept": ["Assets", "Assets"],
                "fiscal_period_end": ["2023-12-31", "2023-12-31"],
                "unit": ["USD", "USD"],
                "accession_number": ["original", "amendment"],
                "value": [100.0, 120.0],
                "available_at": pd.to_datetime(
                    ["2024-02-15 00:00:00+00:00", "2024-03-01 00:00:00+00:00"]
                ),
            }
        )

        before_amendment = select_latest_as_filed(facts, pd.Timestamp("2024-02-20", tz="UTC"))
        after_amendment = select_latest_as_filed(facts, pd.Timestamp("2024-03-02", tz="UTC"))

        self.assertEqual("original", before_amendment.iloc[0]["accession_number"])
        self.assertEqual("amendment", after_amendment.iloc[0]["accession_number"])

    def test_rejects_future_return_column_in_feature_table(self) -> None:
        features = pd.DataFrame({"momentum": [0.1], "forward_return": [0.2]})

        with self.assertRaisesRegex(ValueError, "label"):
            assert_feature_table_excludes_labels(features)


if __name__ == "__main__":
    unittest.main()
