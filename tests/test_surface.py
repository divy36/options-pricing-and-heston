from datetime import datetime,timezone,timedelta
from math import exp
import numpy as np
import pytest
from black_scholes import Inputs,price
from black_scholes.surface import extract,grid_surface
from black_scholes.market_data import load_snapshot


def fixture():
    asof=datetime(2026,9,24,16,tzinfo=timezone.utc)
    payloads=[]
    for days in [30,60,90]:
        expiry=(asof+timedelta(days=days)).date().isoformat()
        p={'expiry':expiry,'retrieved_utc':asof.isoformat(),
           'underlying':{'regularMarketPrice':100,'regularMarketTime':asof.timestamp()},'calls':[],'puts':[]}
        from zoneinfo import ZoneInfo
        end=datetime.fromisoformat(expiry).replace(hour=16,tzinfo=ZoneInfo('America/New_York'))
        t=(end-asof).total_seconds()/31536000
        for strike in [90,95,100,105,110]:
            kind='put' if strike<100*exp(.03*t) else 'call'
            mid=price(Inputs(100,strike,t,.04,.25,.01,kind))
            p['puts' if kind=='put' else 'calls'].append({'contractSymbol':f'{expiry}-{strike}',
                'strike':strike,'bid':mid*.99,'ask':mid*1.01,'openInterest':100,
                'contractSize':'REGULAR','currency':'USD'})
        payloads.append(p)
    return payloads


def test_surface_recovers_flat_vol_without_extrapolation():
    rows,rejected=extract(fixture(),.04,.01)
    assert not rejected
    assert all(abs(r['iv']-.25)<1e-6 for r in rows)
    xs,ts,z,diag=grid_surface(rows)
    assert np.allclose(z[np.isfinite(z)],.25,atol=1e-6)
    assert np.isnan(z[:,0]).all() and np.isnan(z[:,-1]).all()
    assert diag['calendar_total_variance_decreases']==0
    assert all(r['iv_bid']<r['iv']<r['iv_ask'] for r in rows)


@pytest.mark.parametrize('change,reason',[
    ({'bid':0},'missing_zero_or_crossed_quote'),
    ({'ask':-1},'missing_zero_or_crossed_quote'),
    ({'openInterest':0},'low_open_interest'),
    ({'contractSize':'MINI'},'nonstandard_contract'),
    ({'bid':float('nan')},'missing_zero_or_crossed_quote')])
def test_quote_rejections(change,reason):
    p=fixture(); p[0]['calls'][0].update(change)
    rows,reject=extract(p,.04,.01)
    assert reject[0]['reason']==reason


def test_timestamp_and_sparse_grid():
    p=fixture(); p[0]['underlying']['regularMarketTime']-=10*86400
    with pytest.raises(ValueError,match='timestamp'): extract(p,.04,.01)
    rows,_=extract(fixture()[:1],.04,.01)
    with pytest.raises(ValueError,match='three expiries'): grid_surface(rows)


def test_snapshot_tampering(tmp_path):
    import json
    (tmp_path/'manifest.json').write_text(json.dumps({'files':[{'file':'a.json','sha256':'wrong'}]}))
    (tmp_path/'a.json').write_text('{}')
    with pytest.raises(ValueError,match='checksum'): load_snapshot(tmp_path)
