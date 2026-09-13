import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.build_universe_prototype import load_cached_history


class UniverseCacheTest(unittest.TestCase):
    def test_restores_a_datetime_index_from_cached_yfinance_csv(self) -> None:
        history = pd.DataFrame(
            {"Close": [10.0], "Volume": [100]},
            index=pd.DatetimeIndex(["2024-01-02 00:00:00-05:00"], name="Date"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ABC.csv"
            history.to_csv(path)
            restored = load_cached_history(path)

        self.assertIsInstance(restored.index, pd.DatetimeIndex)
        self.assertEqual(2024, restored.index.year[0])


if __name__ == "__main__":
    unittest.main()
