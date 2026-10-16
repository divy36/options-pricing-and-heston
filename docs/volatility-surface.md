# SPY market volatility surface

## Completed observation

Retrieved 24 September 2026 at 18:13 UTC from Yahoo Finance through yfinance 1.2.0.
Seven expiries run from 9 October 2026 through 17 September 2027. The snapshot
contains 2,237 contracts; 746 pass the specified filters. All 976 tests pass,
including flat-surface recovery, bid/ask-IV ordering, sparse-data handling,
quote filtering, stale underlying rejection and snapshot checksum integrity.
An offline replay reproduced all four CSV/JSON scientific outputs byte for byte.
HTML element identifiers may vary and are outside that equality claim.

## Data and provenance

The original local archive `data/raw/SPY-20260924T181314428297Z` (not bundled) preserves the provider-returned option tables
and underlying metadata as normalized JSON, not original HTTP wire bytes.
The manifest records retrieval times, library version and SHA-256 file hashes.
The loader verifies the hashes before replay. These are real quoted premiums,
not simulated data, executed trades or guaranteed executable midpoint prices.

Underlying source timestamps span 18:13:10–18:13:16 UTC. Yahoo supplies last-trade
timestamps but not individual bid/ask timestamps. Last-trade time is retained
but is NOT treated as quote age. Sequential requests and potentially delayed
quotes prevent claiming a synchronized, independently verified live surface.
The underlying age check allows four days for weekends/holidays; this does not
certify bid/ask freshness. Downloads fail explicitly on missing data or rate limits.
Wait before retrying provider rate limits; do not run high-frequency polling.

## Valuation conventions

Maturity is Actual/365 from each underlying source timestamp to 16:00 New York on
the listed expiry. This is a valuation convention, not an exercise-cutoff model;
early closes, discrete dividends and American exercise are not modelled.
Premiums are USD per share, not per standard 100-share contract.

The base rate is an assumed flat continuously compounded 4%, not downloaded
Treasury/SOFR data. The base continuous dividend yield is Yahoo's trailing annual
dividend yield 0.0073742205 (about 0.7374%), used as a proxy, not a dividend forecast.
Both are configurable through `--rate` and `--dividend`.
Forward F = S exp((r-q)T). European-equivalent IV is solved from each quote's
bid, midpoint and ask using the existing safeguarded solver. Provider IVs and
last-trade prices are retained for reference but never substituted into the fit.

## Filtering

Reject nonstandard/non-USD contracts; missing, nonpositive or crossed quotes;
open interest below 10; spreads over 40% of midpoint; maturity outside 7–400 days;
strike/forward outside 0.7–1.3; and failed European price bounds or IV inversion.
Keep puts for K<F and calls for K>=F to obtain one OTM wing per expiry.
Accepted midpoint IVs must be between 0.5% and 300%. Every rejected row records
the first failing reason. Quality filters reduce problems but cannot prove freshness.

## Surface construction and diagnostics

Interpolate total variance w = sigma² T linearly along log(K/F), then linearly
between adjacent maturities. Recover sigma = sqrt(w/T). Do not extrapolate beyond
observed support. Mask strike intervals wider than 0.08 log-moneyness; require
at least four quotes per slice and three usable slices. The 3D mesh is a
visual interpolation, not additional market observations or an arbitrage-free fit.

The observed run has zero decreasing-total-variance instances among 318
comparable adjacent-expiry grid pairs. This limited diagnostic does not test
butterfly arbitrage, guarantee global calendar consistency or establish executable
arbitrage. American early exercise and assumed carry can distort comparisons.
Bid/ask IV bars display quote uncertainty; they are not statistical confidence intervals.

## Files and replay

- `scripts/build_surface.py`: fetch or offline replay; accepts a ticker and carry assumptions.
- `src/black_scholes/market_data.py`: snapshot retrieval, manifest and checksums.
- `src/black_scholes/surface.py`: quote checks, IV extraction and interpolation.
- `src/black_scholes/surface_report.py`: standalone HTML with embedded Plotly and CSV exports.
- `results/spy-market-surface/surface.html`: interactive report, usable without a server.
- `results/spy-market-surface/accepted_quotes.csv`: actual bid/ask plus recalculated IVs.
- `results/spy-market-surface/rejected_quotes.csv`: excluded contracts and reasons.
- `results/spy-market-surface/surface_grid.csv`: interpolated cells, unsupported cells blank.
- `results/spy-market-surface/summary.json`: run statistics and assumptions.

## Sources

- yfinance API and option-chain examples: https://ranaroussi.github.io/yfinance/
- Maintainer implementation: https://github.com/ranaroussi/yfinance/blob/main/yfinance/ticker.py
- Yahoo SPY option chain: https://finance.yahoo.com/quote/SPY/options/
- Fund information: https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy

This is local research use. Data access does not grant redistribution rights.

## Public repository data

Raw provider JSON snapshots are not bundled. Historical Heston calibration uses
the included screened quote CSV; raw surface replay requires a snapshot you
hold locally. See [data instructions](../data/README.md).
