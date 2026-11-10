"""Download and audit source data, then rebuild the eight-equity research project."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pandas as pd

from us_equity_cross_sectional.research.run_paths import SYMBOLS

ROOT = Path(__file__).resolve().parents[1]
STAGES = (
    "build_asof_fundamental_panel",
    "build_research_panel",
    "run_factor_research",
    "run_model_comparison",
    "run_portfolio",
    "run_transaction_costs",
    "run_robustness",
)


def write_summary(run_dir: Path, snapshot: str, source_names: list[str]) -> None:
    reports = run_dir / "reports"
    factors = pd.read_csv(reports / "factor_metrics.csv")
    models = pd.read_csv(reports / "model_metrics.csv")
    portfolios = pd.read_csv(reports / "portfolio_metrics.csv").set_index("variant")
    costs = pd.read_csv(reports / "transaction_cost_metrics.csv")
    weeks = pd.read_csv(reports / "portfolio_returns_equal_weight.csv")["research_date"]
    lines = [
        "# Cross-sectional equity research run", "",
        f"Price cutoff: {snapshot} (exclusive).",
        f"Input providers as recorded in the cache: {', '.join(source_names)}.",
        f"Portfolio signal dates: {weeks.min()} to {weeks.max()} ({len(weeks)} weeks).", "",
        "## Factor and model results", "",
        "| Top factor by mean 5-day Rank IC | Mean Rank IC |", "|---|---:|",
    ]
    for row in factors.nlargest(5, "mean_ic").itertuples():
        lines.append(f"| {row.factor} | {row.mean_ic:.4f} |")
    lines.extend(["", "| Feature group | Model | Mean OOS Rank IC |", "|---|---|---:|"])
    for row in models.sort_values("mean_ic", ascending=False).itertuples():
        lines.append(f"| {row.feature_group} | {row.model} | {row.mean_ic:.4f} |")
    lines.extend([
        "", "## Price-only Ridge portfolio", "",
        "| Variant | Cost (bps) | Annualized net return | Net Sharpe | Max drawdown |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in costs.itertuples():
        lines.append(
            f"| {row.variant} | {row.cost_bps} | {row.annualized_return:.2%} | "
            f"{row.sharpe_ratio:.3f} | {row.max_drawdown:.2%} |"
        )
    lines.extend([
        "", f"Gross annualized volatility was {portfolios.loc['equal_weight', 'annualized_volatility']:.2%} "
        f"for equal weight and {portfolios.loc['inverse_vol', 'annualized_volatility']:.2%} for inverse volatility.",
        "", "## Interpretation", "",
        "The eight current large-cap names introduce survivorship and selection bias. The Ridge configuration "
        "was carried over from the historical study. Its performance on overlapping dates is descriptive, "
        "and the model comparison is exploratory. Fees use traded notional from gross holdings drift. "
        "Borrow fees, market impact, and capacity are outside this prototype.", "",
    ])
    (reports / "research_summary.md").write_text("\n".join(lines))


def runtime_versions() -> dict[str, str]:
    packages = ("numpy", "pandas", "scikit-learn", "scipy", "lightgbm", "matplotlib", "yfinance", "requests")
    versions = {"python": sys.version.split()[0]}
    for package in packages:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "unavailable"
    return versions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today(),
                        help="Exclusive cutoff for price observations and realized returns (YYYY-MM-DD).")
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="Dedicated output directory, for example runs/2026-09-11.")
    parser.add_argument("--offline", action="store_true",
                        help="Use the original provider caches and audit manifests in this run directory.")
    args = parser.parse_args()
    if not date(2012, 1, 1) <= args.as_of <= date.today():
        parser.error("--as-of must be from 2012-01-01 through today")
    if not args.offline and "@" not in os.environ.get("SEC_USER_AGENT", ""):
        parser.error("Set SEC_USER_AGENT to your name or organization and contact email.")
    run_dir = args.run_dir.resolve()
    if run_dir == ROOT or (ROOT / "reports") in run_dir.parents or run_dir == ROOT / "reports":
        parser.error("--run-dir must be separate from the repository's historical reports")
    run_dir.mkdir(parents=True, exist_ok=True)
    lock = run_dir / ".running"
    try:
        lock.mkdir()
    except FileExistsError:
        parser.error("This run directory is already in use. Choose a different --run-dir.")
    try:
        run_pipeline(run_dir, args.as_of.isoformat(), offline=args.offline)
    finally:
        lock.rmdir()


def run_pipeline(run_dir: Path, snapshot: str, *, offline: bool) -> None:
    marker = run_dir / "completed_run.json"
    if marker.exists():
        raise SystemExit("Choose a new --run-dir for a run with a completion marker.")
    env = dict(os.environ, EQUITY_RUN_DIR=str(run_dir), EQUITY_SNAPSHOT=snapshot)

    def run(stage: str, *flags: str) -> None:
        print(f"\n=== {stage} ===", flush=True)
        result = subprocess.run([sys.executable, "-u", str(ROOT / "scripts" / f"{stage}.py"), *flags], env=env)
        if result.returncode:
            raise SystemExit(f"{stage} failed with exit code {result.returncode}. Outputs so far: {run_dir}")

    if not offline:
        flags = ("--root", str(run_dir), "--snapshot", snapshot)
        # Prices and splits share the provider's retrieval-date basis, even
        # when the research cutoff predates retrieval. Labels still stop at the cutoff.
        run("audit_price_provider", *flags, "--symbols", *SYMBOLS)
        run("audit_sec_fundamentals", *flags)

    manifests = run_dir / "data/manifests"
    expected = {
        f"yfinance_provider_audit_{snapshot}.json": "successful_symbols",
        f"sec_fundamentals_audit_{snapshot}.json": "issuers",
    }
    sources = []
    required = set(SYMBOLS)
    for filename, key in expected.items():
        path = manifests / filename
        if not path.is_file():
            raise SystemExit(f"Missing required provider manifest: {path}")
        manifest = json.loads(path.read_text())
        if not required.issubset(manifest.get(key, ())) or required.intersection(manifest.get("failures", {})):
            raise SystemExit(f"Incomplete provider cache: {path}")
        sources.append(manifest["provider"])

    raw = run_dir / "data/raw"
    price = raw / "yfinance_provider_audit" / snapshot
    sec = raw / "sec_provider_audit" / snapshot
    inputs = [manifests / name for name in expected]
    for symbol in SYMBOLS:
        inputs.extend((price / f"{symbol}.csv", sec / f"{symbol}_companyfacts.json", sec / f"{symbol}_submissions.json"))
    input_hashes = {}
    for path in inputs:
        if not path.is_file():
            raise SystemExit(f"Missing required cached input: {path}")
        input_hashes[str(path.relative_to(run_dir))] = sha256(path.read_bytes()).hexdigest()

    for stage in STAGES:
        run(stage)
    write_summary(run_dir, snapshot, sources)
    marker.write_text(json.dumps({
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "exclusive_sample_cutoff": snapshot,
        "used_cached_provider_inputs": offline,
        "universe": list(SYMBOLS),
        "provider_manifests": list(expected),
        "stages": list(STAGES),
        "versions": runtime_versions(),
        "input_sha256": input_hashes,
    }, indent=2) + "\n")
    print(f"\nResearch run complete: {run_dir / 'reports'}")


if __name__ == "__main__":
    main()
