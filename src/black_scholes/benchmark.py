"""Independent QuantLib adapter. Maturities use exact Actual/365 Fixed days."""
from dataclasses import asdict
from datetime import datetime, timezone
from itertools import product
import csv
import json
from pathlib import Path
import QuantLib as ql
from .model import Inputs, price, greeks


def reference(x):
    days = round(x.maturity * 365)
    if abs(days / 365 - x.maturity) > 1e-12 or days <= 0:
        raise ValueError("QuantLib benchmark requires positive whole-day maturity")
    settings = ql.Settings.instance()
    old = settings.evaluationDate
    today = ql.Date(23, 9, 2026)
    try:
        settings.evaluationDate = today
        dc = ql.Actual365Fixed()
        spot = ql.QuoteHandle(ql.SimpleQuote(x.spot))
        risk = ql.YieldTermStructureHandle(ql.FlatForward(today, x.rate, dc))
        div = ql.YieldTermStructureHandle(ql.FlatForward(today, x.dividend, dc))
        vol = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, ql.NullCalendar(), x.volatility, dc))
        process = ql.BlackScholesMertonProcess(spot, div, risk, vol)
        payoff = ql.PlainVanillaPayoff(ql.Option.Call if x.kind == "call" else ql.Option.Put, x.strike)
        option = ql.VanillaOption(payoff, ql.EuropeanExercise(today + days))
        option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
        return {name: getattr(option, "NPV" if name == "price" else name)()
                for name in ("price", "delta", "gamma", "vega", "theta", "rho")}
    finally:
        settings.evaluationDate = old


def scenarios():
    for strike, days, rate, vol, div, kind in product(
            [50, 80, 100, 120, 200], [1, 7, 30, 365, 1825],
            [-0.02, 0, 0.05], [0.01, 0.2, 1.0], [0, 0.03], ["call", "put"]):
        yield Inputs(100, strike, days / 365, rate, vol, div, kind)


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows, maxima, failures = [], {}, 0
    for x in scenarios():
        own = {"price": price(x), **asdict(greeks(x))}
        ref = reference(x)
        row = asdict(x)
        for name in own:
            error = abs(own[name] - ref[name])
            maxima[name] = max(maxima.get(name, 0), error)
            passed = error <= 1e-9 + 1e-9 * abs(ref[name])
            failures += not passed
            row.update({name: own[name], name + "_quantlib": ref[name], name + "_abs_error": error})
        rows.append(row)
    with (output / "quantlib_comparison.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    summary = {"generated_utc": datetime.now(timezone.utc).isoformat(), "quantlib_version": ql.__version__,
               "scenarios": len(rows), "comparisons": len(rows) * 6, "failed_comparisons": failures,
               "absolute_tolerance": 1e-9, "relative_tolerance": 1e-9, "maximum_absolute_errors": maxima}
    (output / "validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
