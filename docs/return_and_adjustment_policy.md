# Return and Adjustment Policy

| Quantity | V1 field/policy | Reason |
|---|---|---|
| Economic forward return | `adjusted_close` | total-return-like series avoids mechanical corporate-action price discontinuities in the audited provider data |
| Momentum, reversal, volatility | `adjusted_close` | characteristics use economically continuous daily price changes |
| Dollar volume / ADV | `close × split_consistent_volume` | aligns reported volume with Yahoo's back-adjusted historical close basis across splits |
| Amihud-style illiquidity | `abs(adjusted daily return) / (close × split_consistent_volume)` | economic return numerator with a split-consistent trade-value denominator |
| Split-day Amihud | missing observation | avoids relying on uncertain split/volume adjustment compatibility |

The provider returned separate `Dividends` and `Stock Splits`. `Close` already behaves as split-adjusted around audited split events even when `auto_adjust=False`; `Adj Close / Close` differs for dividend-paying issuers. Therefore neither field is called universally “raw.” Both are retained, and the selected use above is a documented convention rather than a claim about Yahoo’s internal methodology.

Known limits remain: Yahoo data may be revised; actions and adjustments may be incomplete; delisting returns and a historical securities master are absent. The current S&P 100 prototype is not survivorship-bias-free. These limits apply to every later result from this panel.

The split audit found that reported volume did not show the multiplier needed to match back-adjusted historical close before AAPL (4:1), NVDA (10:1), TSLA (5:1), and WMT (3:1) splits. ADV and Amihud therefore use a cumulative **future** split factor solely to express historical volume on the same share basis as the already back-adjusted price. This corrects units, not information timing; it remains prototype-quality and is fully documented in the split-consistency audit.
