"""Bracketed bisection and safeguarded Newton implied-volatility solvers."""
from dataclasses import dataclass, replace
from math import isfinite
from .model import price, price_bounds, greeks


@dataclass(frozen=True)
class IVResult:
    volatility: float
    iterations: int
    price_error: float
    method: str


def implied_volatility(target, inputs, method="newton", price_tolerance=1e-10,
                       volatility_tolerance=1e-12, max_iterations=200, max_volatility=16.0):
    if method not in ("newton", "bisection"):
        raise ValueError("method must be newton or bisection")
    if not isfinite(target) or target < 0:
        raise ValueError("target must be finite and nonnegative")
    if inputs.maturity <= 0:
        raise ValueError("implied volatility is not identifiable at expiry")
    if any(not isfinite(v) or v <= 0 for v in (price_tolerance, volatility_tolerance, max_volatility)):
        raise ValueError("tolerances and max_volatility must be finite and positive")
    if not isinstance(max_iterations, int) or max_iterations <= 0:
        raise ValueError("max_iterations must be a positive integer")
    lower, upper = price_bounds(inputs)
    if target < lower or target >= upper:
        raise ValueError("target outside finite-volatility no-arbitrage bounds")
    if target == lower:
        return IVResult(0.0, 0, 0.0, method)
    lo, hi = 0.0, min(0.5, max_volatility)
    while price(replace(inputs, volatility=hi)) < target and hi < max_volatility:
        hi = min(2 * hi, max_volatility)
    if price(replace(inputs, volatility=hi)) < target:
        raise ValueError("could not bracket implied volatility within max_volatility")
    vol = (lo + hi) / 2
    for iteration in range(1, max_iterations + 1):
        x = replace(inputs, volatility=vol)
        error = price(x) - target
        if abs(error) <= price_tolerance:
            return IVResult(vol, iteration, error, method)
        if error > 0:
            hi = vol
        else:
            lo = vol
        if hi - lo <= volatility_tolerance:
            break
        candidate = (lo + hi) / 2
        if method == "newton":
            vega = greeks(x).vega
            if vega > 1e-14:
                newton = vol - error / vega
                if lo < newton < hi:
                    candidate = newton
        vol = candidate
    raise RuntimeError("implied-volatility solver did not meet price tolerance")
