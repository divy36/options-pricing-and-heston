"""Closed-form European call/put prices; rates and volatility are decimals."""
from dataclasses import dataclass
from math import erfc, exp, isfinite, log, pi, sqrt


def cdf(x):
    # erfc retains small left-tail probabilities unlike 1 + erf(x).
    return 0.5 * erfc(-x / sqrt(2))


def pdf(x):
    return exp(-0.5 * x * x) / sqrt(2 * pi)


@dataclass(frozen=True)
class Inputs:
    spot: float
    strike: float
    maturity: float
    rate: float
    volatility: float
    dividend: float = 0.0
    kind: str = "call"

    def __post_init__(self):
        for name in ("spot", "strike", "maturity", "rate", "volatility", "dividend"):
            if not isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if self.spot <= 0 or self.strike <= 0:
            raise ValueError("spot and strike must be positive")
        if self.maturity < 0 or self.volatility < 0:
            raise ValueError("maturity and volatility must be nonnegative")
        if self.kind not in ("call", "put"):
            raise ValueError("kind must be call or put")


def price_bounds(x):
    """Discounted no-arbitrage bounds for European options."""
    a = x.spot * exp(-x.dividend * x.maturity)
    b = x.strike * exp(-x.rate * x.maturity)
    return (max(a - b, 0.0), a) if x.kind == "call" else (max(b - a, 0.0), b)


def terms(x):
    v = x.volatility * sqrt(x.maturity)
    d1 = (log(x.spot / x.strike) + (x.rate - x.dividend) * x.maturity) / v + v / 2
    return d1, d1 - v


def price(x):
    if x.maturity == 0 or x.volatility == 0:
        return price_bounds(x)[0]
    d1, d2 = terms(x)
    a = x.spot * exp(-x.dividend * x.maturity)
    b = x.strike * exp(-x.rate * x.maturity)
    # Calculate the OTM leg directly, then use parity for the ITM leg.
    if a <= b:
        call = max(0.0, a * cdf(d1) - b * cdf(d2))
        return call if x.kind == "call" else call + b - a
    put = max(0.0, b * cdf(-d2) - a * cdf(-d1))
    return put if x.kind == "put" else put + a - b


@dataclass(frozen=True)
class Greeks:
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


def greeks(x):
    """Raw Greeks: vega/rho per 1.0 change; theta per calendar year.

    Singular expiry/zero-volatility cases are deliberately rejected instead of
    assigning arbitrary derivatives at payoff kinks.
    """
    if x.maturity == 0 or x.volatility == 0:
        raise ValueError("Greeks require positive maturity and volatility")
    d1, d2 = terms(x)
    sign = 1 if x.kind == "call" else -1
    dq, dr = exp(-x.dividend * x.maturity), exp(-x.rate * x.maturity)
    delta = sign * dq * cdf(sign * d1)
    gamma = dq * pdf(d1) / (x.spot * x.volatility * sqrt(x.maturity))
    vega = x.spot * dq * pdf(d1) * sqrt(x.maturity)
    theta = (-x.spot * dq * pdf(d1) * x.volatility / (2 * sqrt(x.maturity))
             - sign * x.rate * x.strike * dr * cdf(sign * d2)
             + sign * x.dividend * x.spot * dq * cdf(sign * d1))
    rho = sign * x.strike * x.maturity * dr * cdf(sign * d2)
    return Greeks(delta, gamma, vega, theta, rho)
