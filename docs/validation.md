# Validation results

Executed 23 September 2026 using Python 3.9, QuantLib 1.43 and pytest 8.4.2.

- 968 automated tests passed.
- 900 controlled input scenarios produced 5,400 independent comparisons.
- Zero comparisons failed the tolerance abs(error) <= 1e-9 + 1e-9*abs(reference).

| Quantity | Maximum absolute discrepancy |
|---|---:|
| Price | 8.53e-14 |
| Delta | 2.07e-13 |
| Gamma | 3.84e-13 |
| Vega | 5.99e-13 |
| Theta | 6.08e-12 |
| Rho | 3.98e-13 |

The full machine-readable evidence is in `results/validation_summary.json` and
`results/quantlib_comparison.csv`. Most tests are parameterized scenarios rather
than distinct test functions; the count should be described accordingly.

## Checks beyond library agreement

Tests check a known vanilla price, put–call parity and discounted price bounds,
central finite differences for all five Greeks, both solvers recovering known
volatilities, invalid inputs, solver failure paths and boundary behavior.

## Numerical issues addressed

- Expiry and zero volatility cause division by zero in naive d1/d2 calculations.
  Prices use their limiting payoffs and the Greeks API rejects these boundaries.
- Deep tails can lose precision if the CDF uses 1+erf; erfc retains left-tail values.
- Computing an in-the-money option by subtracting large terms can lose precision;
  the engine prices the opposite leg and uses parity.
- Unconstrained Newton iterations can diverge with low vega. The solver maintains
  a bracket and falls back to bisection.
- Calendar conventions can create apparent model differences. QuantLib and this
  engine share exact whole-day Actual/365 Fixed maturities in the benchmark.
- Vega/rho percentage-point scaling and theta day/year scaling can create factor
  discrepancies. Comparisons consistently use raw annual units.

No failing QuantLib discrepancy was observed in the final grid. The points above
explain implementation choices, not claims of historical defects in another project.
Very low-vega IVs remain ill-conditioned; no market-data calibration or empirical
pricing accuracy has been demonstrated. The grid is broad but not exhaustive.

## CV wording supported by this implementation

- Built a Python European options pricing engine implementing Black–Scholes–Merton
  valuation, five analytical Greeks and safeguarded Newton/bisection implied-volatility solvers.
- Validated prices and sensitivities against QuantLib across 900 scenarios, with
  968 passing parameterized tests covering numerical derivatives, put–call parity,
  solver recovery and boundary conditions.
