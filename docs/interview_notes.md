# Interview Notes — Milestone 3

**What is cross-sectional prediction?** Ranking many stocks at the same date by expected relative future return, rather than forecasting one asset through time.

**Absolute versus relative return?** Absolute forward return is the stock’s executed holding-period return. Relative return subtracts the same-date equal-weight universe mean, making the initial target a stock-selection measure.

**Factor versus feature versus signal versus alpha?** A feature is an input, a factor is a defined characteristic, a signal is a signed ranking score, and alpha is benchmark-relative unexplained return. They are not interchangeable.

**Momentum versus short-term reversal?** Momentum uses intermediate-horizon returns while skipping the latest month; reversal is the negative of short-horizon prior return. They can coexist because their horizons and proposed mechanisms differ.

**Why skip the most recent month in classic momentum?** It reduces overlap with short-term reversal or microstructure effects; it does not guarantee a better result.

**What is realized volatility?** The trailing standard deviation of adjusted daily returns, annualized by \(\sqrt{252}\). Downside volatility emphasizes negative daily returns.

**Why can liquidity matter without alpha?** It constrains capacity and transaction costs, so it changes the economic usefulness of other signals.

**Lookback versus forecast horizon?** Lookback is past input data; forecast horizon is future label data. They must be separated by the execution convention.

**Why must the label start after execution?** A signal formed after close cannot capture that close’s return. Starting at execution prevents same-close look-ahead.

**Why are overlapping labels important?** Shared future returns create dependence and require maturity-aware chronological splits later.

**How can corporate actions corrupt returns?** A mechanical split or dividend adjustment can resemble a huge price move if price fields are mixed without a documented policy.
