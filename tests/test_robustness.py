import unittest

import numpy as np
import pandas as pd

from us_equity_cross_sectional.research.factor_evaluation import yearly_ic_stability


class RobustnessHelperTest(unittest.TestCase):
    def test_yearly_ic_stability_groups_by_calendar_year(self):
        rng = np.random.default_rng(0)
        rows = []
        for i, date in enumerate(pd.date_range("2020-01-03", periods=20, freq="W-FRI")):
            for j in range(5):
                rows.append({
                    "research_date": date, "security_id": f"S{j}",
                    "factor": rng.normal(), "label": rng.normal(),
                })
        panel = pd.DataFrame(rows)
        result = yearly_ic_stability(panel, "factor", "label")
        self.assertIn("year", result.columns)
        self.assertTrue((result["year"].isin([2020])).all())

    def test_yearly_ic_stability_empty_when_no_overlap(self):
        panel = pd.DataFrame({
            "research_date": pd.date_range("2020-01-03", periods=5, freq="W-FRI"),
            "security_id": ["A"] * 5,
            "factor": [np.nan] * 5,
            "label": [1.0] * 5,
        })
        result = yearly_ic_stability(panel, "factor", "label")
        self.assertTrue(result.empty)


if __name__ == "__main__":
    unittest.main()
