# Options Pricing and Heston Model Comparison

European option pricing, implied volatility, analytical Greeks and equity
volatility surfaces, with an independent NumPy Heston implementation calibrated
using SciPy and benchmarked against QuantLib.

## Results

| Validation / experiment | Result |
| --- | --- |
| Black-Scholes-Merton benchmark | 900 scenarios against QuantLib |
| Heston benchmark | 160 scenarios against QuantLib |
| Automated test suite | 982 passing tests in the recorded local run |
| SPY calibration | 501 training quotes and 245 held-out quotes |
| Held-out price RMSE: expiry-specific Black-Scholes | $3.1157 per share |
| Held-out price RMSE: Heston | $0.4823 per share (84.5% lower) |

The holdout consists of strikes from the **same 24 September 2026 snapshot**.
It measures interpolation, not future predictive performance. Only 2.4% of
Heston holdout prices lie inside bid/ask; improved RMSE does not establish
executable prices or a profitable strategy.

## Quick start

Python 3.9+ is supported by the project metadata; CI checks Python 3.11 and 3.12.
From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[comparison,surface,validation]'
python -m black_scholes
python -m black_scholes --kind put --dividend 0.02
python -m pytest -q
```

`requirements-lock.txt` records the original Python 3.9 research environment.
Use the package extras above for a fresh installation on a newer Python version.
The Black-Scholes pricing core uses the standard library; the Heston and surface
extensions use the optional scientific packages.

## Reproduce the saved comparison

No live market download is required:

```sh
python scripts/compare_models.py --output results/reproduced-comparison
python scripts/validate.py
python scripts/validate_heston.py
```

The calibration uses the included screened quotes in
`results/spy-market-surface/accepted_quotes.csv`. Three Heston starting points
are ranked by training error only. Every third unique strike within each expiry
is held out. Parameters, input/code hashes, optimizer diagnostics and numerical
convergence checks are written alongside the report.

- [Comparison report](results/heston-comparison/report.md)
- [Heston methodology](docs/heston-comparison.md)
- [Black-Scholes validation](docs/validation.md)
- [Surface methodology](docs/volatility-surface.md)
- [Data provenance and acquisition](data/README.md)

Download and open [comparison.html](results/heston-comparison/comparison.html)
or [surface.html](results/spy-market-surface/surface.html) locally for interactive
charts. GitHub's file viewer does not execute these HTML reports.

## Implementation

```text
src/black_scholes/
  model.py           Black-Scholes-Merton prices and five analytical Greeks
  implied.py         Bracketed bisection and safeguarded Newton IV solvers
  benchmark.py       Independent QuantLib benchmark construction
  heston.py          Characteristic function and Lewis Fourier integration
  market_data.py     Snapshot acquisition and checksum-verified replay
  surface.py         Quote filtering, implied volatility and surface grid
  surface_report.py  Interactive surface report
scripts/             Calibration, data acquisition and validation commands
tests/               Numerical identities, boundaries and reference checks
docs/                Assumptions, mathematical methods and limitations
results/             Saved benchmarks, screened quotes and comparison reports
```

The repository name reflects both models; the Python import remains
`black_scholes` to preserve the existing interface.

## Assumptions and limitations

- European exercise and continuous dividends approximate American-style SPY options.
- The market study assumes a flat 4% rate and a trailing dividend-yield proxy.
- Heston uses Lewis inversion with Gauss-Legendre quadrature. Doubling the
  resolution and increasing the integration cutoff checks numerical stability.
- The fitted parameters violate the Feller condition; it is reported, not imposed.
- Rates, dividends, volatility and maturity use annual decimal conventions.
  Vega and rho are per unit change; divide by 100 for a percentage-point change.
  Theta is per year; divide by 365 for calendar-day theta.
- Agreement with QuantLib validates implementation consistency, not market realism.

## References

- Heston (1993), [A Closed-Form Solution for Options with Stochastic Volatility](https://doi.org/10.1093/rfs/6.2.327).
- Lewis (2001), [A Simple Option Formula for General Jump-Diffusion and Other Exponential Levy Processes](https://ssrn.com/abstract=282110).
- [QuantLib](https://github.com/lballabio/QuantLib), the independent pricing reference.
