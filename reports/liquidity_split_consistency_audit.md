# Liquidity / Split Consistency Audit

Yahoo `Close` is back-adjusted for splits in the audited histories, while `Volume` does not show the corresponding mechanical pre-split multiplier. Raw `Close × Volume` therefore understates historical dollar volume before a later split.

## AAPL — 4:1 on 2020-08-31

| Date | Close | Adj Close | Volume | Split | Close×Volume | Split-consistent Close×Volume |
|---|---:|---:|---:|---:|---:|---:|
| 2020-08-27 | 125.010 | 121.152 | 155,552,400 | 0.0 | 19,445,605,856 | 77,782,423,425 |
| 2020-08-28 | 124.808 | 120.956 | 187,630,000 | 0.0 | 23,417,631,740 | 93,670,526,961 |
| 2020-08-31 | 129.040 | 125.058 | 225,702,700 | 4.0 | 29,124,674,893 | 29,124,674,893 |
| 2020-09-01 | 134.180 | 130.039 | 151,948,100 | 0.0 | 20,388,394,945 | 20,388,394,945 |
| 2020-09-02 | 131.400 | 127.345 | 200,119,000 | 0.0 | 26,295,635,379 | 26,295,635,379 |

## NVDA — 10:1 on 2024-06-10

| Date | Close | Adj Close | Volume | Split | Close×Volume | Split-consistent Close×Volume |
|---|---:|---:|---:|---:|---:|---:|
| 2024-06-06 | 120.998 | 120.654 | 664,696,000 | 0.0 | 80,426,887,338 | 804,268,873,383 |
| 2024-06-07 | 120.888 | 120.544 | 412,386,000 | 0.0 | 49,852,518,969 | 498,525,189,694 |
| 2024-06-10 | 121.790 | 121.444 | 313,434,100 | 10.0 | 38,173,139,326 | 38,173,139,326 |
| 2024-06-11 | 120.910 | 120.576 | 222,551,200 | 0.0 | 26,908,666,407 | 26,908,666,407 |
| 2024-06-12 | 125.200 | 124.854 | 299,595,000 | 0.0 | 37,509,293,086 | 37,509,293,086 |

## TSLA — 5:1 on 2020-08-31

| Date | Close | Adj Close | Volume | Split | Close×Volume | Split-consistent Close×Volume |
|---|---:|---:|---:|---:|---:|---:|
| 2020-08-27 | 149.250 | 149.250 | 355,395,000 | 0.0 | 53,042,703,750 | 795,640,556,250 |
| 2020-08-28 | 147.560 | 147.560 | 301,218,000 | 0.0 | 44,447,727,345 | 666,715,910,169 |
| 2020-08-31 | 166.107 | 166.107 | 355,123,200 | 5.0 | 58,988,333,681 | 176,965,001,044 |
| 2020-09-01 | 158.350 | 158.350 | 269,523,300 | 0.0 | 42,679,016,200 | 128,037,048,600 |
| 2020-09-02 | 149.123 | 149.123 | 288,528,300 | 0.0 | 43,026,302,855 | 129,078,908,565 |

## WMT — 3:1 on 2024-02-26

| Date | Close | Adj Close | Volume | Split | Close×Volume | Split-consistent Close×Volume |
|---|---:|---:|---:|---:|---:|---:|
| 2024-02-22 | 58.470 | 56.868 | 29,512,800 | 0.0 | 1,725,613,452 | 5,176,840,356 |
| 2024-02-23 | 58.520 | 56.916 | 74,365,800 | 0.0 | 4,351,886,650 | 13,055,659,950 |
| 2024-02-26 | 59.600 | 57.967 | 32,154,800 | 3.0 | 1,916,426,031 | 1,916,426,031 |
| 2024-02-27 | 59.590 | 57.957 | 18,012,700 | 0.0 | 1,073,376,796 | 1,073,376,796 |
| 2024-02-28 | 59.620 | 57.986 | 14,803,300 | 0.0 | 882,572,730 | 882,572,730 |

## Policy

`split_consistent_volume[t] = reported_volume[t] × product(split ratios strictly after t)`. The split event date itself is on the new share basis and is not multiplied by that event’s ratio. ADV uses `Close × split_consistent_volume`; Amihud uses adjusted-return magnitude over that denominator and excludes split dates. This is a provider-basis repair, not proof of exchange-quality consolidated dollar volume; ADV and Amihud remain prototype-quality under Yahoo data.
