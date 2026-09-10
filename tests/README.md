# Test plan

Add unit tests before each pipeline module is considered complete.

Required first tests:

1. `symbol × date` uniqueness and strictly increasing dates per symbol.
2. No feature may use a date after its `asof_date`.
3. Five-session label dates match a hand-calculated fixture.
4. Training labels mature before each next-fold signal date.
5. Zero price movement and zero costs leave NAV unchanged.
6. Incremental transaction cost lowers NAV by the exact fee amount.
