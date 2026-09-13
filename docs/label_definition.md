# Label Definition

For a weekly research date \(t\), daily features use observations through that session’s close. The signal is formed after close and executes at the next observed trading-session close, indexed \(t+1\). If \(P_j\) is adjusted close at trading-session index \(j\), a horizon is the number of close-to-close return intervals after execution:

```text
close t          close t+1                  close t+1+h
signal formed ── execution price P(t+1) ──► exit price P(t+1+h)
                         |------ h return intervals ------|
```

\[
R_h(t) = \frac{P_{t+1+h}}{P_{t+1}} - 1
\]

Thus `forward_return_1d = P[t+2] / P[t+1] - 1`, `forward_return_5d = P[t+6] / P[t+1] - 1`, and `forward_return_20d = P[t+21] / P[t+1] - 1`. The code moves through observed trading rows, not calendar days: a weekend or market holiday changes dates but not the interval count.

Example with signal-day close 100, execution close 102, then subsequent closes 103, 105, 104, 108, 110: `R_1 = 103/102 - 1`; `R_5 = 110/102 - 1`. Synthetic unit tests also verify a 20-interval example.

The relative target is the same-date equal-weight mean subtraction:

\[
\operatorname{relative\_return}_{i,t,h} = R_{i,t,h} - \frac{1}{N_{t,h}}\sum_{j=1}^{N_{t,h}}R_{j,t,h}
\]

Both absolute and relative labels are retained. This makes the first target a stock-selection question, not a market-timing forecast.

At the end of a sample, a row without execution plus all \(h\) later observed sessions receives a missing label; it is never padded or extrapolated. Labels overlap across weekly research dates—for example, adjacent weekly 20D labels share realized returns—so later chronological validation must purge boundary observations whose outcomes have not matured.
