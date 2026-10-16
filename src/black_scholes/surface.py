"""Quote filtering and descriptive total-variance interpolation (not arbitrage-free)."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from math import exp, log, isfinite
from collections import Counter
from dataclasses import replace
import numpy as np
from .model import Inputs, price_bounds
from .implied import implied_volatility


def finite(value):
    return isinstance(value, (int, float)) and isfinite(value)


def extract(payloads, rate, dividend, max_spread=.4, min_oi=10):
    if not all(isfinite(v) for v in [rate, dividend, max_spread]) or not 0 < max_spread <= 2 or min_oi < 0:
        raise ValueError('Invalid surface settings')
    accepted, rejected = [], []
    for payload in payloads:
        underlying = payload['underlying']
        spot = underlying.get('regularMarketPrice')
        stamp = underlying.get('regularMarketTime')
        if not finite(spot) or spot <= 0 or not finite(stamp):
            raise ValueError('Missing underlying price or source timestamp')
        asof = datetime.fromtimestamp(stamp, timezone.utc)
        retrieved = datetime.fromisoformat(payload['retrieved_utc'])
        age = (retrieved-asof).total_seconds()
        if age < -300 or age > 4*86400:
            raise ValueError('Underlying timestamp is inconsistent or older than four days')
        expiry = datetime.fromisoformat(payload['expiry']).replace(hour=16, tzinfo=ZoneInfo('America/New_York'))
        maturity = (expiry-asof).total_seconds()/(365*86400)
        forward = spot*exp((rate-dividend)*maturity)
        for kind, key in [('call','calls'), ('put','puts')]:
            for item in payload[key]:
                row = {'contract': item.get('contractSymbol'), 'expiry': payload['expiry'], 'kind': kind,
                       'strike': item.get('strike'), 'spot': spot, 'forward': forward,
                       'asof_utc': asof.isoformat(), 'retrieved_utc': payload['retrieved_utc'],
                       'maturity': maturity, 'days': maturity*365,
                       'bid': item.get('bid'), 'ask': item.get('ask'),
                       'last_trade_utc': item.get('lastTradeDate'), 'last_price': item.get('lastPrice'),
                       'open_interest': item.get('openInterest'), 'volume': item.get('volume'),
                       'provider_iv': item.get('impliedVolatility')}
                reason = None
                k,b,a = row['strike'],row['bid'],row['ask']
                if item.get('contractSize') != 'REGULAR' or item.get('currency') != 'USD':
                    reason = 'nonstandard_contract'
                elif not finite(k) or k <= 0 or not 7/365 <= maturity <= 400/365:
                    reason = 'invalid_strike_or_maturity'
                elif not finite(b) or not finite(a) or b <= 0 or a < b:
                    reason = 'missing_zero_or_crossed_quote'
                elif not finite(row['open_interest']) or row['open_interest'] < min_oi:
                    reason = 'low_open_interest'
                elif (a-b)/((a+b)/2) > max_spread:
                    reason = 'wide_spread'
                elif (kind=='call' and k < forward) or (kind=='put' and k >= forward):
                    reason = 'not_forward_otm'
                elif not .7 <= k/forward <= 1.3:
                    reason = 'outside_moneyness_window'
                if reason is None:
                    mid = (a+b)/2
                    x = Inputs(spot,k,maturity,rate,.2,dividend,kind)
                    lower,upper = price_bounds(x)
                    if b <= lower or a >= upper:
                        reason = 'european_price_bounds'
                    else:
                        try:
                            ivs = [implied_volatility(v,x,price_tolerance=1e-8).volatility for v in [b,mid,a]]
                            if not .005 < ivs[1] < 3:
                                reason = 'extreme_iv'
                            else:
                                row.update(mid=mid, iv_bid=ivs[0], iv=ivs[1], iv_ask=ivs[2],
                                           log_moneyness=log(k/forward), total_variance=ivs[1]**2*maturity,
                                           relative_spread=(a-b)/mid)
                        except (ValueError,RuntimeError):
                            reason = 'iv_solver_failure'
                if reason:
                    row['reason']=reason
                    rejected.append(row)
                else:
                    accepted.append(row)
    return accepted,rejected


def grid_surface(rows, points=61, max_gap=.08):
    """Interpolate variance only within observed strike support and adjacent expiries.

    Large log-strike gaps are masked; no wing/time extrapolation or arbitrage repair.
    """
    expiries = sorted(set(r['expiry'] for r in rows))
    slices=[]
    xs=np.linspace(log(.7),log(1.3),points)
    for expiry in expiries:
        rs=sorted([r for r in rows if r['expiry']==expiry],key=lambda r:r['log_moneyness'])
        if len(rs)<4:
            continue
        xp=np.array([r['log_moneyness'] for r in rs]); wp=np.array([r['total_variance'] for r in rs])
        w=np.interp(xs,xp,wp,left=np.nan,right=np.nan)
        for j,x in enumerate(xs):
            i=np.searchsorted(xp,x)
            if 0<i<len(xp) and xp[i]-xp[i-1]>max_gap:
                w[j]=np.nan
        slices.append((rs[0]['maturity'],w,expiry))
    if len(slices)<3:
        raise ValueError('Need at least three expiries with four accepted strikes each')
    ts=np.array([s[0] for s in slices]); ws=np.array([s[1] for s in slices])
    if not np.all(np.diff(ts)>0):
        raise ValueError('Maturity ordering inconsistent')
    dense_t=np.linspace(ts[0],ts[-1],60)
    dense_w=np.full((len(dense_t),len(xs)),np.nan)
    for j in range(len(xs)):
        for i in range(len(ts)-1):
            if np.isfinite(ws[i,j]) and np.isfinite(ws[i+1,j]):
                mask=(dense_t>=ts[i]) & (dense_t<=ts[i+1])
                dense_w[mask,j]=np.interp(dense_t[mask],ts[i:i+2],ws[i:i+2,j])
    violations=int(np.sum((np.diff(ws,axis=0)<-1e-10)&np.isfinite(ws[:-1])&np.isfinite(ws[1:])))
    return xs,dense_t,np.sqrt(dense_w/dense_t[:,None]), {
        'usable_expiries':[s[2] for s in slices],
        'calendar_total_variance_decreases':violations,
        'calendar_comparable_pairs':int(np.sum(np.isfinite(ws[:-1])&np.isfinite(ws[1:]))),
        'surface_cells':int(dense_w.size), 'supported_cells':int(np.isfinite(dense_w).sum())}
