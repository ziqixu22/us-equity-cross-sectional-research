# Milestone 3 Factor Data Audit

No IC, ranking, model, or portfolio result is reported here.

Liquidity policy update: ADV and Amihud use split-consistent volume following the four-event audit in `reports/liquidity_split_consistency_audit.md`; they remain prototype-quality Yahoo measures.

## Panel coverage

- Weekly research dates: 871.
- Rows: 84,846; prototype securities: 101.
- Universe is the current S&P 100 snapshot and is not survivorship-bias-free.

## Raw-factor coverage and distribution

| Factor | Present | Missing | 1st pct | Median | 99th pct |
|---|---:|---:|---:|---:|---:|
| momentum_12_1 | 79,629 | 5,217 | -0.420732 | 0.140997 | 1.40659 |
| momentum_6_1 | 82,231 | 2,615 | -0.338775 | 0.0638744 | 0.724461 |
| momentum_3_1 | 83,533 | 1,313 | -0.250914 | 0.0274745 | 0.379494 |
| prior_return_1d | 84,843 | 3 | -0.0513384 | 0.00098048 | 0.0508845 |
| prior_return_5d | 84,744 | 102 | -0.107538 | 0.00373062 | 0.118939 |
| prior_return_20d | 84,439 | 407 | -0.188202 | 0.0139466 | 0.245238 |
| reversal_1d | 84,843 | 3 | -0.0508845 | -0.00098048 | 0.0513384 |
| reversal_5d | 84,744 | 102 | -0.118939 | -0.00373062 | 0.107538 |
| reversal_20d | 84,439 | 407 | -0.245238 | -0.0139466 | 0.188202 |
| realized_vol_20d | 84,439 | 407 | 0.0818324 | 0.21935 | 0.852174 |
| realized_vol_60d | 83,628 | 1,218 | 0.103801 | 0.233867 | 0.783808 |
| downside_vol_20d | 84,439 | 407 | 0.0368305 | 0.140274 | 0.585847 |
| adv_20d | 84,442 | 404 | 1.12973e+08 | 6.85702e+08 | 9.692e+10 |
| adv_60d | 83,630 | 1,216 | 1.20893e+08 | 6.92676e+08 | 9.25746e+10 |
| amihud_20d | 84,208 | 638 | 1.2592e-13 | 1.49014e-11 | 1.31621e-10 |

## Cross-sectional and sector availability

| Current sector | Weekly rows | Symbols | Mean raw-feature availability |
|---|---:|---:|---:|
| Communication Services | 7,716 | 9 | 98.9% |
| Consumer Discretionary | 7,769 | 9 | 98.9% |
| Consumer Staples | 7,839 | 9 | 98.9% |
| Energy | 2,613 | 3 | 98.9% |
| Financials | 13,065 | 15 | 98.9% |
| Health Care | 12,909 | 15 | 98.9% |
| Industrials | 10,978 | 15 | 98.7% |
| Information Technology | 16,731 | 20 | 98.9% |
| Materials | 871 | 1 | 98.9% |
| Real Estate | 1,742 | 2 | 98.9% |
| Utilities | 2,613 | 3 | 98.9% |

Current sector is a present-day availability diagnostic only. It is not historical sector exposure or industry neutralization.
Market capitalization is not present in the prototype input and is therefore unavailable for this audit.

## Label availability

| Label | Present | Missing |
|---|---:|---:|
| forward_return_1d | 84,745 | 101 |
| forward_return_5d | 84,644 | 202 |
| forward_return_20d | 84,341 | 505 |
