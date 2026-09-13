import unittest

import pandas as pd

from us_equity_cross_sectional.fundamentals.market_cap import build_market_cap


class MarketCapTest(unittest.TestCase):
    def signal(self, **overrides):
        row = {
            "security_id": "AAA",
            "signal_time": pd.Timestamp("2024-06-30 21:00:00", tz="UTC"),
            "signal_date": pd.Timestamp("2024-06-30", tz="UTC"),
            "price": 10.0,
            "split_history_complete": True,
        }
        row.update(overrides)
        return pd.DataFrame([row])

    def shares(self, **overrides):
        row = {
            "security_id": "AAA",
            "variable": "shares_outstanding",
            "unit": "shares",
            "value": 100.0,
            "fiscal_period_end": "2024-06-01",
            "available_at": pd.Timestamp("2024-06-05 20:00:00", tz="UTC"),
            "accession_number": "0000000000-24-000001",
            "acceptance_datetime": pd.Timestamp("2024-06-05 20:00:00", tz="UTC"),
            "filed_date": pd.Timestamp("2024-06-05", tz="UTC"),
            "multiple_share_class_flag": False,
        }
        row.update(overrides)
        return pd.DataFrame([row])

    def result(self, signal=None, shares=None, splits=None, **kwargs):
        return build_market_cap(
            self.signal() if signal is None else signal,
            self.shares() if shares is None else shares,
            pd.DataFrame(columns=["security_id", "split_date", "split_ratio"])
            if splits is None
            else splits,
            price_basis_as_of=pd.Timestamp("2026-09-11", tz="UTC"),
            **kwargs,
        )

    def test_positive_valid_shares_produce_market_cap(self):
        result = self.result()
        self.assertTrue(result.loc[0, "market_cap_eligible"])
        self.assertEqual(100.0, result.loc[0, "shares_split_adjusted"])
        self.assertEqual(1000.0, result.loc[0, "market_cap"])
        self.assertFalse(result.loc[0, "multiple_share_class_flag"])
        self.assertIsNone(result.loc[0, "market_cap_limitation_flag"])

    def test_zero_and_negative_shares_are_rejected(self):
        for value in (0.0, -1.0):
            result = self.result(shares=self.shares(value=value))
            self.assertFalse(result.loc[0, "market_cap_eligible"])
            self.assertIn("nonpositive_shares", result.loc[0, "market_cap_limitation_flag"])
            self.assertTrue(pd.isna(result.loc[0, "market_cap"]))

    def test_shares_unavailable_by_signal_time_are_rejected(self):
        shares = self.shares(available_at=pd.Timestamp("2024-07-01", tz="UTC"))
        result = self.result(shares=shares)
        self.assertFalse(result.loc[0, "market_cap_eligible"])
        self.assertEqual("shares_unavailable", result.loc[0, "market_cap_limitation_flag"])
        self.assertTrue(pd.isna(result.loc[0, "market_cap"]))

    def test_exact_acceptance_timestamp_is_preserved(self):
        result = self.result()
        self.assertEqual("acceptance_datetime", result.loc[0, "shares_acceptance_source"])
        self.assertEqual(pd.Timestamp("2024-06-05 20:00:00", tz="UTC"), result.loc[0, "shares_available_at"])

    def test_filing_date_plus_one_day_fallback_is_labeled(self):
        shares = self.shares(
            acceptance_datetime=pd.NaT,
            available_at=pd.Timestamp("2024-06-06", tz="UTC"),
        )
        result = self.result(shares=shares)
        self.assertEqual("filing_date_plus_one_day", result.loc[0, "shares_acceptance_source"])

    def test_aapl_split_normalization_uses_explicit_events(self):
        signal = self.signal(
            security_id="AAPL",
            signal_time=pd.Timestamp("2014-07-15 21:00:00", tz="UTC"),
            signal_date=pd.Timestamp("2014-07-15", tz="UTC"),
            price=20.0,
        )
        shares = self.shares(
            security_id="AAPL",
            value=861_381_000,
            fiscal_period_end="2014-04-11",
            available_at=pd.Timestamp("2014-04-23", tz="UTC"),
            acceptance_datetime=pd.Timestamp("2014-04-23", tz="UTC"),
        )
        splits = pd.DataFrame({
            "security_id": ["AAPL", "AAPL"],
            "split_date": ["2014-06-09", "2020-08-31"],
            "split_ratio": [7.0, 4.0],
        })
        result = self.result(signal, shares, splits)
        self.assertEqual(28.0, result.loc[0, "split_adjustment_factor"])
        self.assertEqual(861_381_000 * 28, result.loc[0, "shares_split_adjusted"])
        self.assertEqual(861_381_000 * 28 * 20, result.loc[0, "market_cap"])

    def test_nvda_split_normalization_uses_explicit_events(self):
        signal = self.signal(
            security_id="NVDA",
            signal_time=pd.Timestamp("2021-08-25 21:00:00", tz="UTC"),
            signal_date=pd.Timestamp("2021-08-25", tz="UTC"),
            price=5.0,
        )
        shares = self.shares(
            security_id="NVDA",
            value=623_000_000,
            fiscal_period_end="2021-05-21",
            available_at=pd.Timestamp("2021-05-28", tz="UTC"),
            acceptance_datetime=pd.Timestamp("2021-05-28", tz="UTC"),
        )
        splits = pd.DataFrame({
            "security_id": ["NVDA", "NVDA"],
            "split_date": ["2021-07-20", "2024-06-10"],
            "split_ratio": [4.0, 10.0],
        })
        result = self.result(signal, shares, splits)
        self.assertEqual(40.0, result.loc[0, "split_adjustment_factor"])
        self.assertEqual(623_000_000 * 40, result.loc[0, "shares_split_adjusted"])

    def test_stale_shares_are_rejected(self):
        result = self.result(shares=self.shares(fiscal_period_end="2024-02-20"), staleness_limit_days=130)
        self.assertFalse(result.loc[0, "market_cap_eligible"])
        self.assertIn("stale_shares", result.loc[0, "market_cap_limitation_flag"])

    def test_multiple_share_class_flag_rejects_market_cap(self):
        result = self.result(shares=self.shares(multiple_share_class_flag=True))
        self.assertFalse(result.loc[0, "market_cap_eligible"])
        self.assertTrue(result.loc[0, "multiple_share_class_flag"])
        self.assertIn("multiple_share_class_unresolved", result.loc[0, "market_cap_limitation_flag"])
        self.assertTrue(pd.isna(result.loc[0, "market_cap"]))

    def test_unit_and_split_basis_failures_are_rejected(self):
        unit = self.result(shares=self.shares(unit="USD"))
        self.assertFalse(unit.loc[0, "market_cap_eligible"])
        self.assertIn("unit_mismatch", unit.loc[0, "market_cap_limitation_flag"])
        basis = self.result(signal=self.signal(split_history_complete=False))
        self.assertFalse(basis.loc[0, "market_cap_eligible"])
        self.assertIn("split_basis_unresolved", basis.loc[0, "market_cap_limitation_flag"])


if __name__ == "__main__":
    unittest.main()
