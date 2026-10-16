"""Fetch a new equity option snapshot or replay a preserved snapshot offline."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
from black_scholes.market_data import download,load_snapshot
from black_scholes.surface_report import build_report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--symbol',default='SPY')
    p.add_argument('--snapshot',type=Path,help='Replay existing snapshot without network access')
    p.add_argument('--output',type=Path)
    p.add_argument('--rate',type=float,default=.04,help='Flat continuous rate assumption, decimal; default 0.04')
    p.add_argument('--dividend',type=float,help='Continuous yield assumption; default provider trailing yield proxy')
    a=p.parse_args()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    snapshot=a.snapshot or download(a.symbol,Path('data/raw')/(a.symbol+'-'+stamp))
    manifest,payloads=load_snapshot(snapshot)
    output=a.output or Path('results')/('surface-'+manifest['symbol']+'-'+stamp)
    result=build_report(manifest,payloads,output,a.rate,a.dividend)
    print(json.dumps({'snapshot':str(snapshot),'output':str(output),**result},indent=2))


if __name__=='__main__':
    main()
