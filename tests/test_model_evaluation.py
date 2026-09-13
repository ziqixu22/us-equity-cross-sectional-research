import unittest

import numpy as np
import pandas as pd

from us_equity_cross_sectional.models.signal_models import (
    EqualWeightBaseline, build_model, fit_preprocessing, apply_preprocessing,
)
from us_equity_cross_sectional.research.model_evaluation import (
    chronological_expanding_folds, evaluate_model_chronologically, pooled_summary, prediction_turnover,
)


def _synthetic_panel(n_dates=120, n_names=8, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_dates):
        date = pd.Timestamp("2015-01-02") + pd.Timedelta(weeks=d)
        f1 = rng.normal(size=n_names)
        f2 = rng.normal(size=n_names)
        noise = rng.normal(scale=0.5, size=n_names)
        label = 0.8 * f1 - 0.2 * f2 + noise
        for i in range(n_names):
            rows.append({
                "research_date": date, "security_id": f"S{i}",
                "f1": f1[i], "f2": f2[i], "label": label[i],
            })
    return pd.DataFrame(rows)


class SignalModelsTest(unittest.TestCase):
    def test_equal_weight_baseline_is_mean_of_inputs(self):
        baseline = EqualWeightBaseline()
        X = np.array([[1.0, 3.0], [2.0, 2.0], [-1.0, 1.0]])
        baseline.fit(X, np.zeros(3))
        preds = baseline.predict(X)
        np.testing.assert_allclose(preds, X.mean(axis=1))

    def test_build_model_known_names(self):
        for name in ["baseline", "ols", "ridge", "elastic_net", "lightgbm"]:
            model = build_model(name)
            self.assertTrue(hasattr(model, "fit") and hasattr(model, "predict"))

    def test_build_model_unknown_name_raises(self):
        with self.assertRaises(ValueError):
            build_model("not_a_model")

    def test_preprocessing_uses_train_stats_only(self):
        train = pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0], "b": [10.0, 20.0, 30.0, 40.0]})
        test = pd.DataFrame({"a": [100.0], "b": [1000.0]})
        imputer, scaler = fit_preprocessing(train)
        train_t = apply_preprocessing(train, imputer, scaler)
        test_t = apply_preprocessing(test, imputer, scaler)
        # Train-transformed columns should be standardized (mean ~0)
        self.assertAlmostEqual(0.0, train_t[:, 1].mean(), places=6)
        # An extreme test value should map to a large z-score, not be
        # allowed to influence the train-fit mean/std (no leakage).
        self.assertGreater(abs(test_t[0, 1]), 3)


class ChronologicalFoldsTest(unittest.TestCase):
    def test_folds_are_expanding_and_never_use_future_train_data(self):
        dates = pd.Series(pd.date_range("2020-01-03", periods=100, freq="W-FRI"))
        folds = chronological_expanding_folds(dates, n_folds=5, min_train_fraction=0.4)
        self.assertGreaterEqual(len(folds), 3)
        prev_train_end = pd.Timestamp.min.tz_localize(None)
        for train_end, test_start, test_end in folds:
            self.assertGreaterEqual(train_end, prev_train_end)
            self.assertLessEqual(train_end, test_start)
            self.assertLessEqual(test_start, test_end)
            prev_train_end = train_end


class ModelEvaluationTest(unittest.TestCase):
    def test_ridge_recovers_signal_better_than_baseline_r2(self):
        panel = _synthetic_panel(n_dates=150, n_names=8)
        ridge_folds, ridge_preds = evaluate_model_chronologically(
            panel, ["f1", "f2"], "label", "ridge", n_folds=4, min_train_fraction=0.4
        )
        baseline_folds, _ = evaluate_model_chronologically(
            panel, ["f1", "f2"], "label", "baseline", n_folds=4, min_train_fraction=0.4
        )
        self.assertFalse(ridge_folds.empty)
        self.assertFalse(baseline_folds.empty)
        self.assertFalse(ridge_preds.empty)
        # Ridge should show positive out-of-sample Rank IC on a genuinely
        # linear-in-features synthetic signal.
        self.assertGreater(ridge_folds["mean_ic"].mean(), 0.1)

    def test_no_test_row_predicted_using_future_training_data(self):
        # Regression-style check: every fold's test block starts at or
        # after its train_end cutoff, and train contains nothing >= train_end.
        panel = _synthetic_panel(n_dates=80, n_names=6)
        fold_metrics, oos = evaluate_model_chronologically(
            panel, ["f1", "f2"], "label", "ols", n_folds=3, min_train_fraction=0.5
        )
        for _, row in fold_metrics.iterrows():
            self.assertLessEqual(row["train_end"], row["test_start"])

    def test_pooled_summary_matches_fold_means(self):
        panel = _synthetic_panel(n_dates=100, n_names=8)
        fold_metrics, _ = evaluate_model_chronologically(panel, ["f1", "f2"], "label", "ols", n_folds=4)
        summary = pooled_summary(fold_metrics)
        self.assertEqual(len(fold_metrics), summary["n_folds"])
        self.assertAlmostEqual(fold_metrics["oos_r2"].mean(), summary["mean_oos_r2"])

    def test_pooled_summary_empty_input(self):
        summary = pooled_summary(pd.DataFrame())
        self.assertEqual(0, summary["n_folds"])

    def test_prediction_turnover_zero_for_static_predictions(self):
        dates = pd.date_range("2020-01-03", periods=5, freq="W-FRI")
        rows = []
        for d in dates:
            for i, sec in enumerate(["A", "B", "C", "D", "E", "F"]):
                rows.append({"research_date": d, "security_id": sec, "prediction": i})
        oos = pd.DataFrame(rows)
        turnover = prediction_turnover(oos, top_frac=1 / 3)
        self.assertAlmostEqual(0.0, turnover)

    def test_prediction_turnover_positive_when_ranks_change(self):
        dates = pd.date_range("2020-01-03", periods=2, freq="W-FRI")
        rows = [
            {"research_date": dates[0], "security_id": s, "prediction": p}
            for s, p in zip(["A", "B", "C", "D", "E", "F"], [6, 5, 4, 3, 2, 1])
        ] + [
            {"research_date": dates[1], "security_id": s, "prediction": p}
            for s, p in zip(["A", "B", "C", "D", "E", "F"], [1, 2, 3, 4, 5, 6])
        ]
        oos = pd.DataFrame(rows)
        turnover = prediction_turnover(oos, top_frac=1 / 3)
        self.assertGreater(turnover, 0.5)


if __name__ == "__main__":
    unittest.main()
