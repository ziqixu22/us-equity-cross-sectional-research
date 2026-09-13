"""Stage 4: apply turnover-based trading costs to the Stage 3 portfolio return series."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from us_equity_cross_sectional.portfolio.long_short import cumulative_nav, portfolio_performance_metrics

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports/figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
COST_BPS = (0, 5, 10, 20, 50)


def apply_costs(returns: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    """net_return = gross_return - trading_cost, cost = turnover * gross_exposure * cost_bps.

    Turnover here is the fraction of the combined long+short name set that
    changed since the prior rebalance (see ``long_short.build_weekly_long_short_returns``).
    Trading a name in or out means trading its full leg weight, so the
    realistic dollar amount traded that week is turnover * gross_exposure
    (200%) of the book, each side of which pays ``cost_bps`` on the
    notional traded. The first rebalance has undefined turnover (no prior
    portfolio to trade from) and is excluded from the cost-adjusted series
    rather than assigned a fabricated cost.
    """
    out = returns.dropna(subset=["turnover"]).copy()
    cost_rate = cost_bps / 10_000
    out["trading_cost"] = out["turnover"] * out["gross_exposure"] * cost_rate
    out["net_return"] = out["portfolio_return"] - out["trading_cost"]
    return out


def main() -> None:
    equal = pd.read_csv(ROOT / "reports/portfolio_returns_equal_weight.csv")
    risk_adj = pd.read_csv(ROOT / "reports/portfolio_returns_inverse_vol.csv")
    equal["research_date"] = pd.to_datetime(equal["research_date"])
    risk_adj["research_date"] = pd.to_datetime(risk_adj["research_date"])

    rows = []
    nav_curves = {}
    for variant_name, returns in [("equal_weight", equal), ("inverse_vol", risk_adj)]:
        for bps in COST_BPS:
            costed = apply_costs(returns, bps)
            metrics = portfolio_performance_metrics(costed, return_column="net_return")
            rows.append({"variant": variant_name, "cost_bps": bps, **metrics})
            if bps in (0, 10, 50):
                nav_curves[(variant_name, bps)] = cumulative_nav(costed, return_column="net_return")

    summary = pd.DataFrame(rows)
    summary.to_csv(ROOT / "reports/transaction_cost_metrics.csv", index=False)
    print(summary.round(4).to_string(index=False))

    # Cost sensitivity figure: annualized net return and Sharpe vs cost, per variant
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for variant_name, group in summary.groupby("variant"):
        axes[0].plot(group["cost_bps"], group["annualized_return"] * 100, marker="o", label=variant_name)
        axes[1].plot(group["cost_bps"], group["sharpe_ratio"], marker="o", label=variant_name)
    axes[0].axhline(0, color="black", linewidth=0.8)
    axes[0].set_xlabel("Cost (bps per unit turnover-notional)")
    axes[0].set_ylabel("Annualized net return (%)")
    axes[0].set_title("Net return vs. cost")
    axes[0].legend()
    axes[1].axhline(0, color="black", linewidth=0.8)
    axes[1].set_xlabel("Cost (bps)")
    axes[1].set_ylabel("Net Sharpe ratio")
    axes[1].set_title("Net Sharpe vs. cost")
    axes[1].legend()
    plt.tight_layout()
    fig.savefig(FIG_DIR / "transaction_cost_sensitivity.png", dpi=140)
    plt.close(fig)

    # Cumulative net NAV at 0/10/50 bps
    fig, ax = plt.subplots(figsize=(10, 5))
    for (variant_name, bps), nav in nav_curves.items():
        ax.plot(nav["research_date"], nav["nav"], label=f"{variant_name}, {bps}bps")
    ax.axhline(1.0, color="black", linewidth=0.8)
    ax.set_title("Cumulative net NAV at selected cost levels")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIG_DIR / "transaction_cost_nav.png", dpi=140)
    plt.close(fig)

    # Simple breakeven-like estimate: linear interpolation of annualized
    # return vs cost to find where it crosses zero (defensible only as a
    # local linear approximation, not a precise breakeven claim).
    print("\nApprox. breakeven cost (linear interpolation between adjacent grid points):")
    for variant_name, group in summary.groupby("variant"):
        group = group.sort_values("cost_bps")
        breakeven = None
        for i in range(len(group) - 1):
            r0, r1 = group["annualized_return"].iloc[i], group["annualized_return"].iloc[i + 1]
            c0, c1 = group["cost_bps"].iloc[i], group["cost_bps"].iloc[i + 1]
            if (r0 > 0) != (r1 > 0):
                breakeven = c0 + (0 - r0) / (r1 - r0) * (c1 - c0)
                break
        print(f"  {variant_name}: {'~%.1f bps' % breakeven if breakeven else 'not reached within tested grid (0-50 bps)'}")


if __name__ == "__main__":
    main()
