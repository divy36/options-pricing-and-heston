# SPY: Black–Scholes–Merton versus Heston

Saved snapshot: 2026-09-24T18:13:14.644372+00:00. 501 training and 245 held-out quotes across seven expiries.

| Model | Split | Price RMSE ($/share) | IV RMSE (percentage points) | Within bid/ask |
|---|---|---:|---:|---:|
| BSM constant volatility | train | 3.3298 | 10.340 | 0.8% |
| BSM constant volatility | holdout | 3.3317 | 9.570 | 0.4% |
| BSM expiry-specific volatility | train | 3.1096 | 11.507 | 1.2% |
| BSM expiry-specific volatility | holdout | 3.1157 | 11.066 | 0.8% |
| Heston stochastic volatility | train | 0.4923 | 3.252 | 3.8% |
| Heston stochastic volatility | holdout | 0.4823 | 3.033 | 2.4% |

## Interpretation and controls

Heston has five fitted parameters; constant-volatility BSM has one, and expiry-specific BSM has seven. All models minimise unweighted training price residuals; near-the-money dollar errors consequently receive more influence than cheap-wing relative errors. Three bounded Heston starts are ranked on training loss only. Held-out strikes are every third unique strike within each expiry, not future market observations. This measures interpolation on one snapshot, not predictive or trading performance.

Heston parameters: {"kappa": 4.6063394123080785, "rho": -0.6231865555418679, "sigma": 1.2523212009131357, "theta": 0.045696842373692204, "v0": 0.017240650994927584}. Feller margin: -1.147318; the Feller condition is reported, not imposed. Parameters at bounds: []. Increasing quadrature from 256 nodes / cutoff 400 to 512 / 600 changes prices by at most $0.00013489.

SPY options are American; these models price European exercise with continuous dividends. The flat 4% rate and trailing dividend-yield proxy are inherited from the original surface. Residuals may reflect exercise, dividends, asynchronous quotes, spread and model misspecification. No claim of arbitrage, executable pricing or profitable trading is made.

Reproduce: `PYTHONPATH=src .venv/bin/python scripts/compare_models.py`. Inputs and code are hashed in summary.json. Calibration trials, all predictions, failure counts and train/holdout metrics are saved alongside this report.
