"""European Heston pricing by Lewis Fourier integration (continuous dividends).

The characteristic function uses the decaying-exponential Heston form. Prices
are not clipped: quadrature errors remain visible to validation callers.
"""
from dataclasses import dataclass
from functools import lru_cache
import numpy as np


@dataclass(frozen=True)
class HestonParameters:
    v0: float
    kappa: float
    theta: float
    sigma: float
    rho: float

    def __post_init__(self):
        if not all(np.isfinite(x) for x in (self.v0, self.kappa, self.theta, self.sigma, self.rho)):
            raise ValueError('Heston parameters must be finite')
        if min(self.v0, self.kappa, self.theta, self.sigma) <= 0 or abs(self.rho) >= 1:
            raise ValueError('Positive variance/reversion/vol-of-vol and |rho| < 1 required')

    @property
    def feller_margin(self):
        return 2 * self.kappa * self.theta - self.sigma**2


@lru_cache(maxsize=8)
def _quadrature(nodes, upper):
    x, w = np.polynomial.legendre.leggauss(nodes)
    return (x + 1) * upper / 2, w * upper / 2


def characteristic(u, maturity, p):
    """CF of log(S_T / forward), including the -variance/2 drift."""
    b = p.kappa - p.rho * p.sigma * 1j * u
    d = np.sqrt(b * b + p.sigma**2 * (u*u + 1j*u))
    g = (b - d) / (b + d)
    decay = np.exp(-d * maturity)
    c = p.kappa * p.theta / p.sigma**2 * (
        (b-d)*maturity - 2*np.log((1-g*decay)/(1-g)))
    variance_loading = (b-d)/p.sigma**2 * (1-decay)/(1-g*decay)
    return np.exp(c + variance_loading*p.v0)


def heston_prices(spot, strikes, maturity, rate, dividend, parameters,
                  kinds='call', nodes=256, upper=400.0):
    """Vector of European prices for one maturity; maturity uses year fractions."""
    strikes = np.atleast_1d(np.asarray(strikes, dtype=float))
    if not np.all(np.isfinite(strikes)) or np.any(strikes <= 0):
        raise ValueError('Strikes must be finite and positive')
    if not all(np.isfinite(x) for x in (spot, maturity, rate, dividend)) or spot <= 0 or maturity < 0:
        raise ValueError('Invalid spot, maturity, rate or dividend')
    kinds = np.broadcast_to(np.asarray(kinds), strikes.shape)
    if np.any((kinds != 'call') & (kinds != 'put')):
        raise ValueError('kind must be call or put')
    if not isinstance(nodes, int) or nodes < 16 or not np.isfinite(upper) or upper <= 0:
        raise ValueError('Invalid quadrature settings')
    if maturity == 0:
        return np.where(kinds == 'call', np.maximum(spot-strikes, 0), np.maximum(strikes-spot, 0))
    forward = spot*np.exp((rate-dividend)*maturity)
    u, weights = _quadrature(nodes, float(upper))
    kernel = characteristic(u-0.5j, maturity, parameters)/(u*u+0.25)
    integrals = np.real(np.exp(1j*np.outer(np.log(forward/strikes), u))*kernel) @ weights
    calls = np.exp(-rate*maturity)*(forward - np.sqrt(forward*strikes)*integrals/np.pi)
    return np.where(kinds == 'call', calls, calls-spot*np.exp(-dividend*maturity)+strikes*np.exp(-rate*maturity))
