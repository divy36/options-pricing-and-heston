"""Portable interactive Plotly report with the actual quote observations visible."""
import csv
import html
import json
from collections import Counter
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
from .surface import extract,grid_surface


def csv_write(path, rows):
    if not rows:
        path.write_text('')
        return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


def build_report(manifest,payloads,output,rate=.04,dividend=None):
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    if dividend is None:
        dividend=payloads[0]['underlying'].get('trailingAnnualDividendYield')
        if dividend is None:
            raise ValueError('Dividend yield unavailable; supply --dividend explicitly')
        dividend_source='Yahoo trailing annual dividend yield; continuous-yield proxy, not a forecast'
    else:
        dividend_source='User-specified continuous dividend yield assumption'
    rows,rejected=extract(payloads,rate,dividend)
    csv_write(output/'accepted_quotes.csv',rows); csv_write(output/'rejected_quotes.csv',rejected)
    xs,ts,z,diag=grid_surface(rows)
    symbol=manifest['symbol']
    summary={'symbol':symbol,'provider':manifest['provider'],'snapshot_start':manifest['retrieval_started_utc'],
             'underlying_asof_utc':sorted(set(r['asof_utc'] for r in rows)),
             'raw_contracts':len(rows)+len(rejected),'accepted_quotes':len(rows),
             'rejection_reasons':dict(Counter(r['reason'] for r in rejected)),
             'rate':rate,'rate_source':'Flat continuously compounded modelling assumption; not a downloaded yield curve',
             'dividend':dividend,'dividend_source':dividend_source,
             'filters':{'max_relative_spread':.4,'min_open_interest':10,'forward_moneyness':[.7,1.3], 'days':[7,400]},
             'diagnostics':diag,'style':'American ETF/equity prices; European-equivalent BSM IV approximation'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2))
    csv_write(output/'surface_grid.csv',[{'forward_moneyness':float(np.exp(x)), 'days':float(t*365),
        'iv':float(z[i,j]) if np.isfinite(z[i,j]) else ''} for i,t in enumerate(ts) for j,x in enumerate(xs)])
    fig=go.Figure(go.Surface(x=np.exp(xs),y=ts*365,z=z*100,colorscale='Viridis',connectgaps=False,
                              colorbar={'title':'IV %'},name='Interpolated IV',opacity=.85))
    fig.add_trace(go.Scatter3d(x=[r['strike']/r['forward'] for r in rows],y=[r['days'] for r in rows],
                  z=[100*r['iv'] for r in rows],mode='markers',marker={'size':2,'color':'#f97316'},
                  text=[r['contract'] for r in rows],name='Observed quote midpoints',
                  hovertemplate='%{text}<br>K/F %{x:.3f}<br>Days %{y:.1f}<br>IV %{z:.2f}%<extra></extra>'))
    fig.update_layout(title=f'{symbol} implied volatility surface',height=650,template='plotly_white',
       scene={'xaxis_title':'Strike / forward','yaxis_title':'Days to expiry','zaxis_title':'Implied volatility %'})
    smiles=go.Figure()
    for expiry in diag['usable_expiries']:
        rr=sorted([r for r in rows if r['expiry']==expiry],key=lambda r:r['strike'])
        smiles.add_trace(go.Scatter(x=[r['strike']/r['forward'] for r in rr],y=[r['iv']*100 for r in rr],
           mode='lines+markers',name=expiry,error_y={'type':'data','symmetric':False,
              'array':[(r['iv_ask']-r['iv'])*100 for r in rr],'arrayminus':[(r['iv']-r['iv_bid'])*100 for r in rr]},
           text=[r['contract'] for r in rr],hovertemplate='%{text}<br>K/F %{x:.3f}<br>IV %{y:.2f}%<extra></extra>'))
    smiles.update_layout(title='Expiry smiles with bid/ask IV ranges',xaxis_title='Strike / forward',yaxis_title='IV %',
                         height=550,template='plotly_white')
    columns=['contract','strike','bid','ask','mid','iv','iv_bid','iv_ask','open_interest']
    table='<table><thead><tr>'+''.join(f'<th>{c}</th>' for c in columns)+'</tr></thead><tbody>'
    for r in rows:
        table+='<tr>'+''.join('<td>'+html.escape(f'{r[c]:.4f}' if isinstance(r[c],float) else str(r[c]))+'</td>' for c in columns)+'</tr>'
    table+='</tbody></table>'
    header=f'''<!doctype html><html><head><meta charset="utf-8"><title>{symbol} volatility surface</title>
<style>body{{font:16px system-ui;margin:35px auto;max-width:1250px;color:#172033;background:#fafbfd}}h1{{font-size:36px}}p{{line-height:1.6}}.cards{{display:flex;gap:20px}}.card{{background:#fff;border:1px solid #ddd;padding:20px;border-radius:10px;flex:1}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{padding:7px;border-bottom:1px solid #ddd;text-align:right}}th{{position:sticky;top:0;background:#eee}}.quotes{{max-height:420px;overflow:auto}}</style></head><body>
<h1>{symbol} option volatility surface</h1><p>Real Yahoo Finance option bid/ask snapshot • {html.escape(manifest['retrieval_started_utc'])}</p>
<div class="cards"><div class="card"><b>{len(rows)}</b> accepted quotes</div><div class="card"><b>{len(diag['usable_expiries'])}</b> expiry slices</div><div class="card"><b>{len(rejected)}</b> excluded quotes</div></div>
<p>American-style options, shown as <b>European-equivalent Black–Scholes IV</b>. Data may be delayed; individual bid/ask timestamps are unavailable. Quotes were fetched sequentially, not as a synchronized exchange snapshot. Orange points are recalculated quote-mid IVs; the surface interpolates total variance and leaves unsupported regions blank.</p>
<p>Flat rate assumption: <b>{100*rate:.2f}%</b>. Continuous dividend proxy: <b>{100*dividend:.3f}%</b> ({html.escape(dividend_source)}). Underlying quote times: {html.escape(', '.join(summary['underlying_asof_utc']))}.</p>'''
    body=fig.to_html(full_html=False,include_plotlyjs=True)+smiles.to_html(full_html=False,include_plotlyjs=False)
    tail=f'''<h2>Data quality and interpretation</h2><p>{diag['calendar_total_variance_decreases']} of {diag['calendar_comparable_pairs']} comparable grid pairs have decreasing total variance across expiries. This is a diagnostic, not proof of executable arbitrage. No arbitrage-free calibration or butterfly-arbitrage repair is applied.</p>
<p>Filters: positive two-sided uncrossed quotes; relative spread ≤40%; open interest ≥10; standard USD contracts; 7–400 days; out-of-the-money relative to the assumed forward; strike/forward 0.7–1.3. No last-trade or provider-IV substitution. Midpoints are not guaranteed execution prices.</p>
<pre>{html.escape(json.dumps(summary['rejection_reasons'],indent=2))}</pre><h2>Accepted market quotes</h2><p>Premiums are USD per share; IV columns are annual decimals. A standard 100-share contract premium is 100 times the listed price.</p><div class="quotes">{table}</div>
<p>Exports: accepted_quotes.csv, rejected_quotes.csv, surface_grid.csv and summary.json. Preserved provider-returned snapshots and SHA-256 hashes support offline replay.</p></body></html>'''
    (output/'surface.html').write_text(header+body+tail)
    return summary
