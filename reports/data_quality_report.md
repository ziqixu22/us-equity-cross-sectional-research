# Data Quality Report — Milestone 2

Generated: 2026-09-11T23:58:18.965640+00:00

## Prototype universe

- Source: current S&P 100 constituent table (https://en.wikipedia.org/wiki/S%26P_100).
- Candidate securities: 101; successful yfinance histories: 101; request failures: 0.
- Eligible now: 100 after close >= $5.00, 60-day ADV >= $10,000,000, and at least 252 daily observations.
- This is a frozen current-constituent prototype, not a historical membership or survivorship-bias-free universe.

## Coverage through time

| Year | Securities with any downloaded history |
|---:|---:|
| 2010 | 94 |
| 2011 | 94 |
| 2012 | 96 |
| 2013 | 97 |
| 2014 | 97 |
| 2015 | 97 |
| 2016 | 97 |
| 2017 | 97 |
| 2018 | 97 |
| 2019 | 98 |
| 2020 | 99 |
| 2021 | 99 |
| 2022 | 99 |
| 2023 | 99 |
| 2024 | 100 |
| 2025 | 100 |
| 2026 | 101 |

## Liquidity and identifier diagnostics

- 60-day ADV (available candidates): min $387,072,907; median $1,269,637,923; max $39,929,208,362.
- Symbols converted from dot to dash for Yahoo compatibility: BRK-B.
- Failed symbols: none.
- Raw bars are cached locally outside Git; the committed snapshot records only the selection and aggregate metadata.
