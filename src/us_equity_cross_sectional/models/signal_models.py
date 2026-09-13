"""Model factory for out-of-sample factor-combination signals.

Every model here is fit only on data a chronological split has marked as
"train" (see ``research/model_evaluation.py``); this module contains no
splitting logic itself, only model construction and the shared
preprocessing pipeline (median-impute, then standardize, both fit on
train only).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import ElasticNet, LinearRegression, Ridge
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

try:
    from lightgbm import LGBMRegressor
    _HAS_LIGHTGBM = True
except ImportError:  # pragma: no cover - environment-dependent
    _HAS_LIGHTGBM = False


class EqualWeightBaseline:
    """No fitting: average the already-standardized factors with equal weight.

    This is the "simple equal-weight standardized factor combination"
    baseline the task asks for -- every included factor contributes with
    equal weight and its predefined sign (no sign is chosen by fitting).
    It expects its input to already be median-imputed and standardized by
    the shared ``fit_preprocessing``/``apply_preprocessing`` pipeline below
    (the same pipeline every other model in this module is fed), so it
    performs no preprocessing of its own -- just the mean across columns.
    """

    def fit(self, X: np.ndarray, y: np.ndarray) -> "EqualWeightBaseline":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.mean(X, axis=1)


def build_model(name: str):
    """Return an unfitted model by name. Raises for an unknown/unavailable name."""
    if name == "baseline":
        return EqualWeightBaseline()
    if name == "ols":
        return LinearRegression()
    if name == "ridge":
        return Ridge(alpha=1.0, random_state=0)
    if name == "elastic_net":
        # alpha=0.01 (a common sklearn default-adjacent starting point) drove
        # every coefficient to exactly zero on this panel's weak, noisy
        # per-factor signal -- a real, reported finding (see
        # reports/model_comparison.md), not silently patched away. alpha is
        # lowered here only so this model produces a non-degenerate
        # (non-constant) prediction to compare against Ridge/OLS at all;
        # this is an ordinary regularization-strength choice, not tuning
        # toward a target performance number.
        return ElasticNet(alpha=0.0005, l1_ratio=0.5, random_state=0, max_iter=5000)
    if name == "lightgbm":
        if not _HAS_LIGHTGBM:
            raise ImportError("lightgbm is not installed in this environment")
        return LGBMRegressor(
            n_estimators=200, max_depth=3, num_leaves=7, learning_rate=0.05,
            min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
            random_state=0, verbosity=-1,
        )
    raise ValueError(f"unknown model name: {name}")


def fit_preprocessing(train_X: pd.DataFrame) -> tuple[SimpleImputer, StandardScaler]:
    """Median-impute then standardize, both fit on TRAIN data only."""
    imputer = SimpleImputer(strategy="median")
    imputer.fit(train_X)
    imputed = imputer.transform(train_X)
    scaler = StandardScaler()
    scaler.fit(imputed)
    return imputer, scaler


def apply_preprocessing(X: pd.DataFrame, imputer: SimpleImputer, scaler: StandardScaler) -> np.ndarray:
    return scaler.transform(imputer.transform(X))
