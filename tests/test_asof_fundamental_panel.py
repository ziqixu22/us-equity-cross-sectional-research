import unittest
import pandas as pd
from us_equity_cross_sectional.fundamentals.asof_panel import build_weekly_fundamental_panel


class AsofPanelTest(unittest.TestCase):
    def signals(self, dates=("2024-06-07",), **extra):
        frame = pd.DataFrame({"research_date": pd.to_datetime(list(dates)), "security_id": "AAA", "signal_time": pd.to_datetime([f"{d} 21:00:00+00:00" for d in dates]), "price": 10.0, "split_history_complete": True})
        for key, value in extra.items(): frame[key] = value
        return frame

    def facts(self):
        rows=[]
        for fp, end, val in [("Q1","2023-03-31",10),("Q2","2023-06-30",22),("Q3","2023-09-30",35),("FY","2023-12-31",50)]:
            rows.append(dict(security_id="AAA", cik="1", variable="revenue", taxonomy="us-gaap", concept="Revenue", unit="USD", kind="duration", value=val, fiscal_period_end=end, fiscal_period_start="2023-01-01", fiscal_year=2023, fiscal_period=fp, form="10-Q", accession_number=f"rev-{fp}", filed_date="2024-01-02", acceptance_datetime="2024-01-02 20:00:00+00:00", available_at="2024-01-02 20:00:00+00:00", mapping_confidence="standard"))
        rows += [dict(security_id="AAA", cik="1", variable=v, taxonomy="us-gaap", concept=v, unit="USD", kind="instant", value=100, fiscal_period_end="2024-05-01", fiscal_period_start=None, fiscal_year=2024, fiscal_period="Q1", form="10-Q", accession_number=v, filed_date="2024-05-02", acceptance_datetime="2024-05-02 20:00:00+00:00", available_at="2024-05-02 20:00:00+00:00", mapping_confidence="standard") for v in ("assets","liabilities","stockholders_equity","cash")]
        rows.append(dict(security_id="AAA", cik="1", variable="shares_outstanding", taxonomy="dei", concept="EntityCommonStockSharesOutstanding", unit="shares", kind="instant", value=100, fiscal_period_end="2024-05-01", fiscal_period_start=None, fiscal_year=2024, fiscal_period="Q1", form="10-Q", accession_number="shares", filed_date="2024-05-02", acceptance_datetime="2024-05-02 20:00:00+00:00", available_at="2024-05-02 20:00:00+00:00", mapping_confidence="standard", multiple_share_class_flag=False))
        return pd.DataFrame(rows)

    def panel(self, signals=None, facts=None):
        return build_weekly_fundamental_panel(self.signals() if signals is None else signals, self.facts() if facts is None else facts, pd.DataFrame(columns=["security_id","split_date","split_ratio"]), price_basis_as_of=pd.Timestamp("2024-06-07", tz="UTC"), market_data_download_timestamp="2024-06-08T00:00:00Z")

    def test_asof_and_amendment_selection(self):
        facts=self.facts(); amended=facts.iloc[[4]].copy(); amended["value"]=200; amended["accession_number"]="assets-amended"; amended["available_at"]="2024-06-10 20:00:00+00:00"; facts=pd.concat([facts,amended],ignore_index=True)
        early=self.panel(self.signals(("2024-06-07",)),facts); late=self.panel(self.signals(("2024-06-14",)),facts)
        self.assertEqual(100, early.loc[0,"assets"]); self.assertEqual(200,late.loc[0,"assets"])
        self.assertEqual("assets-amended",late.loc[0,"assets_accession"])

    def test_ttm_lineage_stock_and_market_cap(self):
        result=self.panel()
        self.assertEqual(50,result.loc[0,"revenue_ttm"]); self.assertEqual('["rev-Q1", "rev-Q2", "rev-Q3", "rev-FY"]',result.loc[0,"revenue_ttm_component_accessions"])
        self.assertEqual(100,result.loc[0,"assets"]); self.assertTrue(result.loc[0,"market_cap_eligible"]); self.assertEqual(1000,result.loc[0,"market_cap"])

    def test_unavailable_stale_multiple_class_and_unique_keys(self):
        facts=self.facts(); facts.loc[facts.variable.eq("shares_outstanding"),"multiple_share_class_flag"]=True
        signals=self.signals(("2024-06-07","2024-06-14")); result=self.panel(signals,facts)
        self.assertFalse(result.market_cap_eligible.any()); self.assertFalse(result.duplicated(["research_date","security_id"]).any())
        stale=self.panel(self.signals(("2024-12-01",)),self.facts()); self.assertTrue(pd.isna(stale.loc[0,"market_cap"]))


if __name__ == "__main__": unittest.main()
