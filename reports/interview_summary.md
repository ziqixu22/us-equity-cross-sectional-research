# Interview Summary

## 30-second explanation

"I built a small point-in-time equity research pipeline to test whether
price and fundamental signals can rank stocks by future relative returns,
and whether machine learning beats a simple factor combination after
costs. On my 8-stock prototype universe, a handful of price and volatility
factors showed a modest, fold-stable positive signal; fundamentals didn't
add anything on top of them, and a gradient-boosted tree underperformed a
plain Ridge regression. The resulting long-short portfolio had a gross
Sharpe around 0.6-0.8 and survived — though was significantly eroded by —
realistic trading costs. I reported every negative finding, not just the
positive one."

## 2-minute explanation

"The research question was whether price, liquidity, volatility, and
point-in-time fundamental signals can rank U.S. equities by future
cross-sectional returns, and whether ML can improve on a traditional
factor combination out-of-sample, after costs.

I built the data pipeline point-in-time from the ground up: SEC EDGAR
fundamentals keyed by filing acceptance timestamp rather than fiscal
period end, so a company's earnings are only usable once they were
actually filed, plus a cached Yahoo Finance price feed. On top of that I
computed 11 price/technical factors and 8 fundamental factors, and
validated each with cross-sectional Spearman Rank IC — not raw
correlation, since I only care about relative ranking, not levels — across
1D, 5D, and 20D horizons, with quantile spreads and year-by-year stability
checks.

The strongest factors were realized volatility, dollar-volume liquidity,
and 12-1 month momentum, each with a mean Rank IC around 0.03-0.05.
Fundamentals were weaker and, when I combined them with price factors in a
linear model using strictly chronological expanding-window
cross-validation — never a random split, since that would leak future
information — they didn't add anything; some fundamental factors even hurt
a combined model slightly. I also tested a shallow LightGBM model against
Ridge and OLS, and the nonlinear model underperformed the linear ones in
every feature group I tried, most likely because the sample is too small
for a tree ensemble to find generalizable nonlinear structure.

I picked Ridge on price factors as the production candidate — not because
it had the single best in-sample number, but because it was positive in
all six of its out-of-sample folds and didn't depend on the
lower-coverage, data-quality-flagged fundamentals. I built a dollar-neutral
tercile long-short portfolio from that signal, which had a gross Sharpe of
0.6-0.8 over 13 years of weekly out-of-sample rebalances, then applied a
turnover-based transaction-cost model at 0 to 50 basis points. The net
Sharpe survived — stayed positive — across that whole range but dropped
substantially at the higher end, which tells you the edge is real but
thin.

The biggest limitation is that this is only an 8-stock universe, so every
number here is illustrative of the methodology more than a production
claim. I documented that, and every other null or negative finding, in a
dedicated failure-analysis report rather than only presenting the
positive result."

## Detailed technical explanation

**What problem did you study?** Whether a small set of point-in-time price
and fundamental signals predicts which stocks will outperform their peers
over the next 5 trading days, and whether combining those signals with
machine learning — rather than a naive equal-weight average — improves
that prediction out-of-sample, net of realistic trading costs.

**Why cross-sectional ranking rather than absolute return prediction?**
Absolute return prediction is dominated by market-wide moves that are
extremely hard to predict and not the point of a long-short strategy.
Ranking stocks against each other on the same date isolates the
relative-performance signal a market-neutral portfolio can actually
monetize, and it's a much more tractable prediction target statistically.

**Why relative returns as the label, not raw forward returns?** Because
the portfolio I ultimately build is dollar-neutral — it only cares about
which names do better or worse than the cross-sectional average that
period, not the market's overall direction. Using `forward_return -
equal_weight_mean_that_date` as the label directly matches what the
downstream long-short portfolio is actually trying to capture.

**Why point-in-time data?** Any backtest that uses information not
actually available on the decision date overstates performance — this is
the single most common way a quant backtest silently cheats. I keyed every
fundamental value off SEC filing acceptance timestamps specifically to
avoid using a quarter's numbers before they were actually public.

**Why Rank IC as the primary metric instead of R²?** I found, empirically,
that pooled out-of-sample R² is numerically unusable at this sample size —
some folds have such low target variance that R²'s denominator nearly
vanishes, producing values as extreme as -1.55 billion in one ablation.
That's a real, investigated finding (I checked the label distribution and
ruled out a code bug), not something to explain away — and it's exactly
why Rank IC, which is scale-free and much more stable with small samples,
is the right primary metric here.

**Why chronological, not random, out-of-sample splits?** A random
train/test split lets the model see data from after the test period during
training, which is a direct information leak in any time-series setting.
I used strictly expanding-window folds — train is everything before a
cutoff date, test is the next block of weeks — matching how the strategy
would actually be run live.

**Why Ridge before the nonlinear model?** Ridge (and OLS) beat LightGBM
out-of-sample in every one of the three feature groups I tested. With only
8 securities and a noisy target, a shallow tree ensemble has enough
capacity to fit training-period idiosyncrasies that don't generalize, while
a linear model's much lower variance is an advantage at this scale. I
picked the model the data actually supported, not the more sophisticated
one.

**What did ML actually add?** Modestly, not much beyond what a
well-chosen linear combination of price factors already captured.
ElasticNet's raw mean IC was marginally higher than Ridge's, but I picked
Ridge anyway because it was consistently positive across all 6 folds and
ElasticNet had degenerated to a constant model at its default
regularization strength before I retuned it — a red flag about its
robustness I wasn't willing to paper over. The nonlinear model added
nothing measurable; if anything, it hurt.

**What failed?** Fundamentals added no incremental signal and sometimes
hurt a combined model; the nonlinear model underperformed linear models in
every configuration; the strongest individual factor was still negative in
several individual years; R² was numerically unusable; ElasticNet
degenerated at its default hyperparameter. All of this is in
`reports/failure_analysis.md`.

**What survived costs?** Net Sharpe stayed positive across the entire
0-50 bps cost grid for both portfolio variants, though it dropped from
0.61/0.82 gross to 0.05/0.18 at 50 bps — a large but not fatal erosion.

**Biggest limitation?** The 8-security universe. Every result here should
be read as a methodology demonstration, not a production-scale finding —
IC values, Sharpe ratios, and stability checks would all need to be
re-validated on a much larger universe before drawing any real investment
conclusion.

**What would you improve with CRSP/Compustat?** A licensed, survivorship-
bias-free universe of hundreds to thousands of names, letting me re-run
every factor and model evaluation at a scale where Rank IC and quantile
spreads are statistically meaningful rather than illustrative, and letting
me properly test whether the fundamentals null result is a data-quality
artifact (I found two specific unresolved defects in this project's SEC
ingestion) or a genuine finding.

**How would you scale this to institutional research?** Move from 8 names
to a full liquid universe with proper survivorship-bias controls; replace
the single inverse-volatility scalar with a real risk model and optimizer
once diversification is meaningful; add a market-impact-aware cost model
appropriate to intended trade size; and formalize the significance testing
to account for cross-sectional and time-series autocorrelation rather than
the naive t-statistics used in this prototype.
