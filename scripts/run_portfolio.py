"""Stage 3: build and evaluate the long-short portfolio from the selected Stage 2 signal."""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from us_equity_cross_sectional.portfolio.long_short import (
    build_weekly_long_short_returns, cumulative_nav, portfolio_performance_metrics,
)
from us_equity_cross_sectional.research.model_evaluation import evaluate_model_chronologically

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports/figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

PRICE_FACTORS = [
    "momentum_12_1", "momentum_6_1", "momentum_3_1",
    "reversal_1d", "reversal_5d", "reversal_20d",
    "realized_vol_20d", "realized_vol_60d", "downside_vol_20d",
    "adv_20d", "amihud_20d",
]
LABEL = "relative_return_5d"


def main() -> None:
    panel = pd.read_csv(ROOT / "data/processed/research_panel_2026-09-11.csv")
    panel["research_date"] = pd.to_datetime(panel["research_date"])

    # Reproduce the Stage 2-selected signal (price_only + ridge) explicitly,
    # rather than reusing the "best by raw mean IC" file Stage 2 saved
    # (which picked elastic_net) -- Stage 2's report explains why Ridge was
    # selected as the defensible choice despite not having the single
    # highest mean IC.
    fold_metrics, oos = evaluate_model_chronologically(
        panel, PRICE_FACTORS, LABEL, "ridge", n_folds=6, min_train_fraction=0.4
    )
    oos = oos.merge(panel[["research_date", "security_id", "forward_return_5d"]], on=["research_date", "security_id"], how="left")
    oos.to_csv(ROOT / "data/processed/ridge_price_only_oos_predictions.csv", index=False)

    equal = build_weekly_long_short_returns(oos, panel, weighting="equal")
    risk_adj = build_weekly_long_short_returns(oos, panel, weighting="inverse_vol")
    equal.to_csv(ROOT / "reports/portfolio_returns_equal_weight.csv", index=False)
    risk_adj.to_csv(ROOT / "reports/portfolio_returns_inverse_vol.csv", index=False)

    metrics_equal = portfolio_performance_metrics(equal)
    metrics_risk = portfolio_performance_metrics(risk_adj)
    summary = pd.DataFrame([{"variant": "equal_weight", **metrics_equal}, {"variant": "inverse_vol", **metrics_risk}])
    summary.to_csv(ROOT / "reports/portfolio_metrics.csv", index=False)
    print(summary.round(4).to_string(index=False))

    nav_equal = cumulative_nav(equal)
    nav_risk = cumulative_nav(risk_adj)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(nav_equal["research_date"], nav_equal["nav"], label="Equal-weight")
    ax.plot(nav_risk["research_date"], nav_risk["nav"], label="Inverse-vol weighted")
    ax.axhline(1.0, color="black", linewidth=0.8)
    ax.set_title("Cumulative NAV: top-tercile long / bottom-tercile short (5D, OOS only)")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIG_DIR / "portfolio_cumulative_return.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.fill_between(nav_equal["research_date"], nav_equal["drawdown"], 0, color="#c0392b", alpha=0.6, label="Equal-weight")
    ax.plot(nav_risk["research_date"], nav_risk["drawdown"], color="#2c3e50", label="Inverse-vol")
    ax.set_title("Drawdown")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIG_DIR / "portfolio_drawdown.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(equal["research_date"], equal["turnover"])
    ax.set_title("Weekly turnover (equal-weight variant)")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "portfolio_turnover.png", dpi=140)
    plt.close(fig)

    print("\nsaved reports/portfolio_metrics.csv, portfolio_returns_*.csv, and 3 figures")


if __name__ == "__main__":
    main()
