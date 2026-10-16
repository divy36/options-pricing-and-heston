import itertools
import numpy as np
import pytest
from black_scholes.heston import HestonParameters, heston_prices
from black_scholes.model import Inputs, price


def test_quantlib_reference_grid():
    ql = pytest.importorskip('QuantLib')
    old = ql.Settings.instance().evaluationDate
    today = ql.Date(1, 1, 2026)
    ql.Settings.instance().evaluationDate = today
    errors = []
    try:
        for p, days, strike, kind in itertools.product([
            HestonParameters(.04, 2, .04, .3, -.7),
            HestonParameters(.025, 1, .06, .6, -.5),
            HestonParameters(.09, 3, .04, .4, .3),
            HestonParameters(.017, 4.6, .046, 1.25, -.62),
        ], [15, 90, 365, 730], [70, 85, 100, 115, 130], ['call', 'put']):
            dc = ql.Actual365Fixed()
            r = ql.YieldTermStructureHandle(ql.FlatForward(today, .04, dc))
            q = ql.YieldTermStructureHandle(ql.FlatForward(today, .01, dc))
            process = ql.HestonProcess(r, q, ql.QuoteHandle(ql.SimpleQuote(100)), p.v0, p.kappa, p.theta, p.sigma, p.rho)
            option = ql.VanillaOption(ql.PlainVanillaPayoff(ql.Option.Call if kind == 'call' else ql.Option.Put, strike), ql.EuropeanExercise(today+days))
            option.setPricingEngine(ql.AnalyticHestonEngine(ql.HestonModel(process), 192))
            actual = heston_prices(100, [strike], days/365, .04, .01, p, kind, nodes=512, upper=600)[0]
            errors.append(abs(actual-option.NPV()))
        assert max(errors) < 2e-5, max(errors)
    finally:
        ql.Settings.instance().evaluationDate = old


def test_constant_variance_limit():
    p = HestonParameters(.04, 2, .04, .0001, -.5)
    for strike in [80, 100, 120]:
        actual = heston_prices(100, [strike], 1, .04, .01, p)[0]
        assert actual == pytest.approx(price(Inputs(100, strike, 1, .04, .2, .01)), abs=.0003)


def test_parity_bounds_and_quadrature():
    p = HestonParameters(.04, 2, .05, .5, -.7)
    ks = np.array([70, 90, 100, 110, 130])
    calls = heston_prices(100, ks, .5, .04, .01, p)
    puts = heston_prices(100, ks, .5, .04, .01, p, 'put')
    np.testing.assert_allclose(calls-puts, 100*np.exp(-.005)-ks*np.exp(-.02), atol=1e-12)
    assert np.all(calls >= np.maximum(100*np.exp(-.005)-ks*np.exp(-.02),0)-1e-7)
    assert np.all(np.diff(calls) < 0)
    np.testing.assert_allclose(calls, heston_prices(100, ks, .5, .04, .01, p, nodes=512, upper=600), atol=1e-5)


@pytest.mark.parametrize('args', [(-1,2,.04,.3,-.7),(.04,0,.04,.3,-.7),(.04,2,.04,.3,1)])
def test_invalid_parameters(args):
    with pytest.raises(ValueError): HestonParameters(*args)
