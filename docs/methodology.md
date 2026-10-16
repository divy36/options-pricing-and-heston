# Model and numerical methodology

Let S be spot, K strike, T remaining years, r the continuously compounded risk-free
rate, q the continuous dividend yield, and sigma annual volatility. Under the
risk-neutral model, dS = (r-q)S dt + sigma S dW. Assumptions include European
exercise, constant coefficients, lognormal positive prices, frictionless trading
and continuous hedging. Negative rates are allowed.

Define N as the standard normal CDF and phi as its density:

```
d1 = [ln(S/K) + (r-q+sigma²/2)T] / (sigma sqrt(T))
d2 = d1 - sigma sqrt(T)
A = S exp(-qT), B = K exp(-rT)
call = A N(d1) - B N(d2)
put  = B N(-d2) - A N(-d1)
```

For sign s=+1 for calls and -1 for puts:

```
delta = s exp(-qT) N(s d1)
gamma = exp(-qT) phi(d1) / (S sigma sqrt(T))
vega  = S exp(-qT) phi(d1) sqrt(T)
theta = -S exp(-qT) phi(d1) sigma/(2 sqrt(T))
        -s r K exp(-rT) N(s d2) + s q S exp(-qT) N(s d1)
rho   = s K T exp(-rT) N(s d2)
```

Theta is minus the derivative with respect to remaining maturity. Greeks are
raw sensitivities, not percentage-point or daily-scaled values.

## Numerical treatment

The normal CDF uses erfc to avoid losing small left-tail probabilities. The
out-of-the-money leg is evaluated directly and the in-the-money leg follows
from put–call parity, reducing subtraction error. Double precision still has
limits for vanishing option prices and extreme finite inputs.

At T=0 the engine returns intrinsic value. At sigma=0 it returns the discounted
deterministic payoff. The Greeks API rejects both boundaries: payoff kinks make
some derivatives undefined and assigning arbitrary values would be misleading.
The engine requires strictly positive S and K and finite numerical inputs.

For implied volatility, the lower bound is max(A-B,0) for calls or max(B-A,0)
for puts; the upper bound is A or B. Prices outside these bounds are rejected.
The upper bound has no finite implied volatility. At an exactly equal lower
bound the API returns the zero-volatility boundary solution; numerical rounding
can make tiny positive volatility indistinguishable from zero.

The upper bracket expands until the target is enclosed or the configured cap is
reached (default sigma=16). Bisection halves the interval. Safeguarded Newton
uses the analytical vega only when its candidate remains inside the bracket,
otherwise falling back to bisection. Failure to meet the absolute price tolerance
raises an exception. A small price residual does not guarantee an accurate IV
when vega is near zero; round-trip IV tests therefore use identifiable scenarios.

## Independent comparison conventions

QuantLib builds its own spot handle, flat continuous risk and dividend curves,
constant volatility surface, European payoff, exercise and analytic engine.
Both implementations use Actual/365 Fixed with whole-day maturities. The
adapter restores QuantLib's global evaluation date after each call and is
intended for sequential use, not concurrent threads.

The grid fixes S=100 and crosses strikes 50/80/100/120/200, maturities
1/7/30/365/1825 days, rates -2%/0%/5%, volatilities 1%/20%/100%, yields 0%/3%,
and both option types: 900 scenarios and 5,400 price/Greek comparisons.
Acceptance is absolute error <= 1e-9 + 1e-9 * abs(reference).
Numerical finite differences independently check the Greek derivatives.
