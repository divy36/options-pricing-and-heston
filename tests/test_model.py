from dataclasses import replace
from math import exp
import pytest
from black_scholes import Inputs, price, greeks, price_bounds, implied_volatility
from black_scholes.benchmark import reference, scenarios

BASE = Inputs(100, 100, 1, .05, .2)


def test_known_price():
    assert price(BASE) == pytest.approx(10.450583572185565, abs=1e-12)
    assert price(replace(BASE, kind="put")) == pytest.approx(5.573526022256971, abs=1e-12)


@pytest.mark.parametrize("x", list(scenarios()))
def test_quantlib_and_parity(x):
    expected = reference(x)
    actual = {"price": price(x), **vars(greeks(x))}
    for name in actual:
        assert actual[name] == pytest.approx(expected[name], abs=1e-9, rel=1e-9)
    c, p = price(replace(x, kind="call")), price(replace(x, kind="put"))
    assert c - p == pytest.approx(x.spot * exp(-x.dividend*x.maturity) - x.strike*exp(-x.rate*x.maturity), abs=1e-12)
    low, high = price_bounds(x)
    assert low - 1e-12 <= price(x) <= high + 1e-12


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("strike", [80, 100, 120])
def test_finite_difference_greeks(kind, strike):
    x = replace(BASE, kind=kind, strike=strike, dividend=.02)
    g = greeks(x)
    for field, name, h, sign in [("spot", "delta", .001, 1), ("volatility", "vega", 1e-5, 1),
                                  ("rate", "rho", 1e-5, 1), ("maturity", "theta", 1e-5, -1)]:
        up, down = replace(x, **{field: getattr(x, field)+h}), replace(x, **{field: getattr(x, field)-h})
        assert getattr(g, name) == pytest.approx(sign*(price(up)-price(down))/(2*h), rel=1e-7, abs=1e-7)
    h = .01
    gamma = (price(replace(x, spot=x.spot+h))-2*price(x)+price(replace(x, spot=x.spot-h)))/h**2
    assert g.gamma == pytest.approx(gamma, rel=1e-6, abs=1e-8)


@pytest.mark.parametrize("method", ["newton", "bisection"])
@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("vol", [.05, .2, .8, 2.0])
@pytest.mark.parametrize("strike", [90, 100, 110])
def test_iv_roundtrip(method, kind, vol, strike):
    x = replace(BASE, volatility=vol, kind=kind, strike=strike)
    result = implied_volatility(price(x), x, method)
    assert result.volatility == pytest.approx(vol, abs=1e-7)
    assert abs(result.price_error) <= 1e-10


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("strike", [80, 100, 120])
def test_boundaries(kind, strike):
    x = replace(BASE, kind=kind, strike=strike)
    assert price(replace(x, volatility=0)) == price_bounds(x)[0]
    terminal = max((1 if kind == "call" else -1)*(x.spot-x.strike), 0)
    assert price(replace(x, maturity=0)) == terminal
    for boundary in [replace(x, maturity=0), replace(x, volatility=0)]:
        with pytest.raises(ValueError):
            greeks(boundary)
    assert implied_volatility(price_bounds(x)[0], x).volatility == 0
    for target in [-1, price_bounds(x)[1], float("nan")]:
        with pytest.raises(ValueError):
            implied_volatility(target, x)


@pytest.mark.parametrize("field,value", [("spot",0),("strike",-1),("volatility",-.1),("maturity",-1),("rate",float("inf")),("kind","invalid")])
def test_invalid_inputs(field, value):
    with pytest.raises(ValueError):
        replace(BASE, **{field:value})


def test_solver_failures():
    with pytest.raises(ValueError):
        implied_volatility(10, replace(BASE, maturity=0))
    with pytest.raises(ValueError):
        implied_volatility(50, BASE, max_volatility=.1)
    with pytest.raises(RuntimeError):
        implied_volatility(price(BASE), BASE, max_iterations=1)
    with pytest.raises(ValueError):
        implied_volatility(10, BASE, method="unknown")
