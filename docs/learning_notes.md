# Learning Notes — Milestone 3

**Label and forward return.** A label is the future outcome a model would eventually try to predict. Here a forward return begins only after execution: \(P_{t+1+h}/P_{t+1}-1\). A systematic-equities researcher cares because an off-by-one date can manufacture predictive skill from information that could not have been traded.

**Relative return and cross-sectional prediction.** Relative return subtracts the equal-weight same-date universe mean. Cross-sectional prediction asks which stock should outperform peers, rather than whether one asset will rise. A researcher cares because stock selection and market timing have different benchmarks, exposures, and validation designs.

**Feature, factor, signal, alpha.** A feature is an input; a factor is a defined characteristic such as momentum; a signal is a signed score intended to rank future returns; alpha is return unexplained by the chosen benchmark/risk model. A researcher cares because positive raw returns or a characteristic exposure are not automatically alpha.

**Momentum and lookback.** Momentum measures an intermediate-horizon return: 12–1 uses \(P_{t-21}/P_{t-252}-1\), so the latest 21 sessions are skipped. The hypothesis is gradual information diffusion or underreaction, not a proven law. A researcher cares because pre-registering windows prevents choosing the strongest-looking historical definition.

**Short-term reversal.** Prior 1D/5D/20D returns are recorded, while reversal is their negative. Momentum and reversal can coexist because they ask about different horizons and mechanisms. A researcher cares because the sign must be fixed before results; reversing it after inspection is factor mining.

**Realized volatility.** This is the annualized standard deviation of adjusted daily returns over a trailing window. Downside volatility uses the root mean square of negative returns. It is a characteristic, not a claimed alpha. A researcher cares because volatility affects risk, portfolio concentration, and apparent return predictability.

**Liquidity.** Average dollar volume approximates tradable activity; Amihud-style illiquidity scales absolute returns by dollar volume. Liquidity can matter without predicting return because it governs capacity, turnover cost, and whether a paper signal can be implemented. A researcher cares because a high-IC but illiquid signal may be unusable.

**Lookback versus forecast horizon.** Lookback is the past data window used to make a feature; forecast horizon is the future interval used for the label. They need not match. A researcher cares because confusing them causes accidental future-data inclusion.

**Holding period and overlapping labels.** A holding period is the intended return interval after execution. Weekly 20D labels overlap, sharing many future daily returns. A researcher cares because later train/validation splits must account for this dependence rather than treating every row as independent.
