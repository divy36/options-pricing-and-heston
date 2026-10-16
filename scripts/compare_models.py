"""Offline BSM / Heston calibration with a deterministic held-out-strike split."""
import argparse
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import time
import numpy as np
import scipy
from scipy.optimize import least_squares
from scipy.special import ndtr
from black_scholes.heston import HestonParameters, heston_prices
from black_scholes.implied import implied_volatility
from black_scholes.model import Inputs

ROOT = Path(__file__).resolve().parents[1]


def bsm(rows, vol, rate, dividend):
    s=np.array([float(x['spot']) for x in rows]); k=np.array([float(x['strike']) for x in rows]); t=np.array([float(x['maturity']) for x in rows])
    d1=(np.log(s/k)+(rate-dividend+.5*vol**2)*t)/(vol*np.sqrt(t)); d2=d1-vol*np.sqrt(t)
    a=s*np.exp(-dividend*t); b=k*np.exp(-rate*t)
    call=a*ndtr(d1)-b*ndtr(d2)
    return np.where([x['kind']=='call' for x in rows],call,call-a+b)


def predict_heston(rows, params, rate, dividend, nodes=256, upper=400):
    result=np.empty(len(rows))
    groups={}
    for i,row in enumerate(rows):
        key=(float(row['spot']),float(row['maturity']))
        groups.setdefault(key,[]).append(i)
    for (s,t),idx in groups.items():
        result[idx]=heston_prices(s,[float(rows[i]['strike']) for i in idx],t,rate,dividend,params,[rows[i]['kind'] for i in idx],nodes,upper)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'results/spy-market-surface')
    parser.add_argument('--output',type=Path,default=ROOT/'results/heston-comparison')
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    source=args.input/'accepted_quotes.csv'; source_summary=args.input/'summary.json'
    rows=list(csv.DictReader(source.open())); meta=json.loads(source_summary.read_text())
    rate,dividend=meta['rate'],meta['dividend']
    # Every third unique strike is held out within each expiry. Same-strike
    # contracts stay in one partition; no random search for a flattering split.
    for expiry in sorted({r['expiry'] for r in rows}):
        strikes=sorted({float(r['strike']) for r in rows if r['expiry']==expiry})
        holdout=set(strikes[2::3])
        for r in rows:
            if r['expiry']==expiry:r['split']='holdout' if float(r['strike']) in holdout else 'train'
    train=[r for r in rows if r['split']=='train']; target=np.array([float(r['mid']) for r in train])
    flat=least_squares(lambda x:bsm(train,x[0],rate,dividend)-target,[.2],bounds=([.02],[1.5]))
    if not flat.success:raise RuntimeError('Constant-volatility calibration failed')
    term={}
    for expiry in sorted({r['expiry'] for r in rows}):
        sample=[r for r in train if r['expiry']==expiry]
        fit=least_squares(lambda x:bsm(sample,x[0],rate,dividend)-[float(r['mid']) for r in sample],[.2],bounds=([.02],[1.5]))
        if not fit.success:raise RuntimeError(f'Term-vol calibration failed: {expiry}')
        term[expiry]=float(fit.x[0])
    lower=[.001,.05,.001,.03,-.95]; upper=[.5,15,.5,2,.95]
    starts=[[.025,2,.04,.4,-.7],[.04,1,.06,.7,-.5],[.02,5,.03,.2,-.3]]
    trials=[]; solutions=[]
    for initial in starts:
        start=time.perf_counter()
        fit=least_squares(lambda x:predict_heston(train,HestonParameters(*x),rate,dividend)-target,initial,bounds=(lower,upper),max_nfev=200,ftol=1e-9,xtol=1e-9,gtol=1e-7,x_scale='jac')
        trial=dict(initial=initial,parameters=asdict(HestonParameters(*fit.x)),success=bool(fit.success),message=fit.message,nfev=fit.nfev,train_rmse=float(np.sqrt(np.mean(fit.fun**2))),seconds=time.perf_counter()-start)
        print(json.dumps(trial),flush=True);trials.append(trial);solutions.append(fit)
    successful=[f for f in solutions if f.success]
    if not successful:raise RuntimeError('No Heston calibration converged')
    best=min(successful,key=lambda f:np.sum(f.fun**2)); p=HestonParameters(*best.x)
    preds={'BSM constant volatility':bsm(rows,flat.x[0],rate,dividend),
           'BSM expiry-specific volatility':bsm(rows,np.array([term[r['expiry']] for r in rows]),rate,dividend),
           'Heston stochastic volatility':predict_heston(rows,p,rate,dividend)}
    refined=predict_heston(rows,p,rate,dividend,nodes=512,upper=600)
    convergence=float(np.max(np.abs(refined-preds['Heston stochastic volatility'])))
    if convergence>.005:raise RuntimeError(f'Quadrature discrepancy above half-cent: {convergence}')
    metrics=[]; detail=[]
    for model,values in preds.items():
        for split in ['train','holdout']:
            ids=[i for i,r in enumerate(rows) if r['split']==split]
            err=np.array([values[i]-float(rows[i]['mid']) for i in ids])
            iv_err=[]; failures=0
            for i in ids:
                r=rows[i]
                try:
                    iv=implied_volatility(float(values[i]),Inputs(float(r['spot']),float(r['strike']),float(r['maturity']),rate,.2,dividend,r['kind'])).volatility
                    iv_err.append((iv-float(r['iv']))*100)
                except (ValueError,RuntimeError):failures+=1
            metrics.append(dict(model=model,split=split,n=len(ids),price_rmse=float(np.sqrt(np.mean(err**2))),price_mae=float(np.mean(np.abs(err))),iv_rmse_percentage_points=float(np.sqrt(np.mean(np.array(iv_err)**2))) if iv_err else None,iv_failures=failures,within_bid_ask_fraction=float(np.mean([float(rows[i]['bid'])<=values[i]<=float(rows[i]['ask']) for i in ids]))))
        for i,r in enumerate(rows):detail.append(dict(model=model,expiry=r['expiry'],strike=r['strike'],kind=r['kind'],split=r['split'],market_mid=r['mid'],model_price=float(values[i]),error=float(values[i])-float(r['mid'])))
    for name,data in [('metrics.csv',metrics),('predictions.csv',detail)]:
        with (args.output/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    summary=dict(snapshot=meta['snapshot_start'],quote_count=len(rows),training_quotes=len(train),holdout_quotes=len(rows)-len(train),rate=rate,dividend=dividend,flat_vol=float(flat.x[0]),expiry_vols=term,heston_parameters=asdict(p),feller_margin=p.feller_margin,bound_hits=[name for name,v,lo,hi in zip(asdict(p),best.x,lower,upper) if min(v-lo,hi-v)<1e-4],quadrature_max_abs_difference=convergence,trials=trials,metrics=metrics,input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_summary_sha256=hashlib.sha256(source_summary.read_bytes()).hexdigest(),code_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),ROOT/'src/black_scholes/heston.py',ROOT/'src/black_scholes/model.py',ROOT/'src/black_scholes/implied.py']},versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__))
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2))
    lines=['# SPY: Black–Scholes–Merton versus Heston','',f'Saved snapshot: {meta["snapshot_start"]}. {len(train)} training and {len(rows)-len(train)} held-out quotes across seven expiries.','', '| Model | Split | Price RMSE ($/share) | IV RMSE (percentage points) | Within bid/ask |','|---|---|---:|---:|---:|']
    for m in metrics:lines.append(f'| {m["model"]} | {m["split"]} | {m["price_rmse"]:.4f} | {m["iv_rmse_percentage_points"]:.3f} | {m["within_bid_ask_fraction"]:.1%} |')
    lines+=['','## Interpretation and controls','', 'Heston has five fitted parameters; constant-volatility BSM has one, and expiry-specific BSM has seven. All models minimise unweighted training price residuals; near-the-money dollar errors consequently receive more influence than cheap-wing relative errors. Three bounded Heston starts are ranked on training loss only. Held-out strikes are every third unique strike within each expiry, not future market observations. This measures interpolation on one snapshot, not predictive or trading performance.','',f'Heston parameters: {json.dumps({k: float(v) for k, v in asdict(p).items()}, sort_keys=True)}. Feller margin: {p.feller_margin:.6f}; the Feller condition is reported, not imposed. Parameters at bounds: {summary["bound_hits"]}. Increasing quadrature from 256 nodes / cutoff 400 to 512 / 600 changes prices by at most ${convergence:.8f}.','', 'SPY options are American; these models price European exercise with continuous dividends. The flat 4% rate and trailing dividend-yield proxy are inherited from the original surface. Residuals may reflect exercise, dividends, asynchronous quotes, spread and model misspecification. No claim of arbitrage, executable pricing or profitable trading is made.','', 'Reproduce: `PYTHONPATH=src .venv/bin/python scripts/compare_models.py`. Inputs and code are hashed in summary.json. Calibration trials, all predictions, failure counts and train/holdout metrics are saved alongside this report.']
    (args.output/'report.md').write_text('\n'.join(lines)+'\n')
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    fig=make_subplots(rows=2,cols=4,subplot_titles=sorted(term))
    colors=['#94a3b8','#f59e0b','#0284c7']
    for j,expiry in enumerate(sorted(term)):
        ids=sorted([i for i,r in enumerate(rows) if r['expiry']==expiry],key=lambda i:float(rows[i]['strike']))
        rr,cc=j//4+1,j%4+1
        fig.add_trace(go.Scatter(x=[float(rows[i]['strike']) for i in ids],y=[float(rows[i]['mid']) for i in ids],mode='markers',name='Market mid',marker=dict(color='#111827',symbol=['circle' if rows[i]['split']=='train' else 'diamond' for i in ids]),showlegend=j==0),rr,cc)
        for color,(model,values) in zip(colors,preds.items()):
            fig.add_trace(go.Scatter(x=[float(rows[i]['strike']) for i in ids],y=[values[i] for i in ids],name=model,mode='lines',line=dict(color=color),showlegend=j==0),rr,cc)
    fig.update_layout(title='SPY model comparison — held-out strikes shown as diamonds',height=760,template='plotly_white')
    fig.update_xaxes(title_text='Strike ($)');fig.update_yaxes(title_text='OTM option price ($/share)')
    fig.write_html(str(args.output/'comparison.html'),include_plotlyjs=True)
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':main()
