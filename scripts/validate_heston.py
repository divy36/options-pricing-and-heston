"""Persist independent QuantLib comparisons for the NumPy Heston pricer."""
import csv
import itertools
import json
from pathlib import Path
import QuantLib as ql
from black_scholes.heston import HestonParameters,heston_prices

out=Path(__file__).resolve().parents[1]/'results/heston-comparison'
out.mkdir(parents=True,exist_ok=True)
today=ql.Date(1,1,2026);old=ql.Settings.instance().evaluationDate
rows=[]
try:
    ql.Settings.instance().evaluationDate=today
    for scenario,(p,days,strike,kind) in enumerate(itertools.product([
        HestonParameters(.04,2,.04,.3,-.7),
        HestonParameters(.025,1,.06,.6,-.5),
        HestonParameters(.09,3,.04,.4,.3),
        HestonParameters(.017,4.6,.046,1.25,-.62)
    ],[15,90,365,730],[70,85,100,115,130],['call','put'])):
        dc=ql.Actual365Fixed()
        r=ql.YieldTermStructureHandle(ql.FlatForward(today,.04,dc));q=ql.YieldTermStructureHandle(ql.FlatForward(today,.01,dc))
        process=ql.HestonProcess(r,q,ql.QuoteHandle(ql.SimpleQuote(100)),p.v0,p.kappa,p.theta,p.sigma,p.rho)
        option=ql.VanillaOption(ql.PlainVanillaPayoff(ql.Option.Call if kind=='call' else ql.Option.Put,strike),ql.EuropeanExercise(today+days))
        option.setPricingEngine(ql.AnalyticHestonEngine(ql.HestonModel(process),192))
        expected=option.NPV()
        value=heston_prices(100,[strike],days/365,.04,.01,p,kind,nodes=512,upper=600)[0]
        rows.append(dict(scenario=scenario,spot=100,strike=strike,maturity=days/365,rate=.04,dividend=.01,kind=kind,**vars(p),numpy_price=value,quantlib_price=expected,abs_error=abs(value-expected)))
finally:ql.Settings.instance().evaluationDate=old
with (out/'quantlib_heston_comparison.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
summary=dict(scenarios=len(rows),max_abs_error=max(r['abs_error'] for r in rows),tolerance=2e-5,quantlib_version=ql.__version__,failed=int(sum(r['abs_error']>2e-5 for r in rows)))
(out/'validation.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
raise SystemExit(bool(summary['failed']))
