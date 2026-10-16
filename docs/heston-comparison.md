# Heston comparison extension

Implemented 12 October 2026. This extends the existing pricing project; these
results were not part of the original September Black–Scholes benchmark.

## Why Heston

Black–Scholes–Merton fixes volatility. Heston models instantaneous variance as a
mean-reverting square-root diffusion and allows correlated shocks to spot and
variance. This supplies a five-parameter model for equity volatility skew and
term structure. Merton jump diffusion addresses discontinuous price jumps and
would be a separate extension. Neither is universally superior.

The NumPy implementation evaluates the risk-neutral characteristic function
with Lewis Fourier inversion and Gauss–Legendre quadrature. It does not call
QuantLib to compute its prices. QuantLib's AnalyticHestonEngine is the independent
reference, used in a 160-scenario call/put grid including positive/negative
correlation, short/long maturities, and Feller-satisfying/violating parameters.
Tests also cover the constant-variance limit, parity, price bounds, monotonicity,
quadrature convergence and invalid parameters.

## Reproduce from the project directory

```sh
.venv/bin/python -m pip install -e '.[comparison,validation]'
PYTHONPATH=src .venv/bin/python scripts/compare_models.py
PYTHONPATH=src .venv/bin/python scripts/validate_heston.py
.venv/bin/python -m pytest -q
```

The comparison uses the preserved 24 September 2026 SPY dataset without a new
market download. Source CSV and metadata hashes, code hashes, library versions,
parameter estimates and all three optimisation trials are stored in summary.json.
The original surface and its 900-scenario BSM benchmark are preserved.

## Experimental design

- 746 screened, forward-out-of-the-money contracts across seven expiries.
- 501 training quotes; every third unique strike within each expiry gives 245
  held-out quotes. No maturity or later-date holdout is claimed.
- One-volatility BSM, seven expiry-specific BSM volatilities, and five-parameter
  Heston use the same training prices, flat rate and dividend proxy.
- Bounded least squares minimises dollar price residuals; Heston uses three
  starting points, selected by training loss only. The Feller condition is
  reported but not imposed; Fourier pricing remains applicable without it.
- Held-out metrics: dollar price RMSE/MAE, implied-volatility RMSE, IV inversion
  failures and percentage inside quoted bid/ask. All predictions are exported.
- Doubling quadrature resolution and extending the integration cutoff verifies
  that the reported improvement is not explained by integration error.

See [results and limitations](../results/heston-comparison/report.md),
[interactive comparison](../results/heston-comparison/comparison.html) and
[QuantLib validation](../results/heston-comparison/validation.json).

European exercise and continuous dividends approximate American SPY options.
One snapshot with an interpolated strike holdout does not establish stability
across market regimes or executable trading performance. The fit violates the
Feller condition and only a small proportion of prices fall inside bid/ask;
reduced RMSE is not the same as an adequately specified market model.

## References

- Heston (1993), *A Closed-Form Solution for Options with Stochastic Volatility
  with Applications to Bond and Currency Options*, Review of Financial Studies,
  https://doi.org/10.1093/rfs/6.2.327
- Lewis (2001), *A Simple Option Formula for General Jump-Diffusion and Other
  Exponential Lévy Processes*, https://ssrn.com/abstract=282110
- QuantLib Heston engine and independent test suite:
  https://github.com/lballabio/QuantLib/blob/master/ql/pricingengines/vanilla/analytichestonengine.cpp
  https://github.com/lballabio/QuantLib/blob/master/test-suite/hestonmodel.cpp
