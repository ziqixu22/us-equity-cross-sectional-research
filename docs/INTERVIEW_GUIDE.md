# Interview Guide — U.S. Equity Cross-Sectional Research

## 60-second walkthrough
I designed the research infrastructure before claiming alpha. The pipeline uses explicit information-availability timestamps, frozen-universe metadata, leakage-safe forward labels, price/liquidity factors, and point-in-time SEC fundamentals with filing-level lineage. The next stages are chronological validation, Rank IC, quintile spreads, and transaction-cost-aware portfolio simulation. I deliberately do not report a final model or backtest until those safeguards are complete.

## Know these ideas
- **Look-ahead bias:** using data not public at the signal time.
- **Survivorship bias:** evaluating historical returns only on today’s surviving companies.
- **Rank IC:** Spearman correlation between predicted and realized cross-sectional return ranks.
- **Point-in-time fundamentals:** fiscal period end is not data availability; filing timestamps govern inclusion.
- **Turnover cost:** a gross long-short return is not investable until trading costs are applied.

## Likely questions
**Why is random cross-validation inappropriate?**  
Adjacent observations share time structure and labels can overlap; random folds leak temporal information. Training data must precede validation and label windows must not overlap improperly.

**Why have no backtest result yet?**  
A backtest is only credible after the data timing, universe assumptions, validation protocol, and cost model are complete. Publishing a number earlier would reward a fragile pipeline.

## Reproduce and learn
1. Draw the signal-date → trade-date → label-end timeline.
2. Derive one factor and the five-day relative-return label.
3. Read `docs/leakage_and_bias.md`.
4. Run timing and panel-invariant tests.
5. Explain the current implementation status precisely.

## Honest boundary
The free prototype uses a current universe and is not survivorship-bias-free; it is research infrastructure, not investment advice.