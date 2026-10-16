"""Read-only Yahoo Finance option snapshots; never substitutes simulated prices."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import json
import re
import time


def download(symbol, directory):
    import yfinance as yf
    if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,9}', symbol):
        raise ValueError('Use a plain equity/ETF ticker')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    yf.set_tz_cache_location(str(Path('data/cache')))
    ticker = yf.Ticker(symbol)
    now = datetime.now(timezone.utc)
    available = list(ticker.options)
    eligible = [d for d in available if 7 <= (datetime.fromisoformat(d).replace(tzinfo=timezone.utc)-now).days <= 400]
    if len(eligible) < 3:
        raise RuntimeError('Fewer than three usable expiries returned; no synthetic fallback')
    selected = sorted(set(min(eligible, key=lambda d: abs((datetime.fromisoformat(d).replace(tzinfo=timezone.utc)-now).days-target))
                          for target in [14, 30, 60, 90, 180, 270, 365]))
    manifest = {'provider': 'Yahoo Finance via yfinance', 'symbol': symbol,
                'retrieval_started_utc': now.isoformat(), 'yfinance_version': yf.__version__,
                'data_status': 'Public snapshot; may be delayed. Bid/ask quote timestamps are not supplied.',
                'available_expiries': available, 'files': []}
    for expiry in selected:
        chain = ticker.option_chain(expiry)
        payload = {'expiry': expiry, 'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                   'underlying': chain.underlying,
                   'calls': json.loads(chain.calls.to_json(orient='records', date_format='iso')),
                   'puts': json.loads(chain.puts.to_json(orient='records', date_format='iso'))}
        raw = json.dumps(payload, indent=2, allow_nan=False).encode()
        name = expiry + '.json'
        (directory / name).write_bytes(raw)
        manifest['files'].append({'file': name, 'sha256': hashlib.sha256(raw).hexdigest()})
        time.sleep(.3)
    manifest['retrieval_finished_utc'] = datetime.now(timezone.utc).isoformat()
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return directory


def load_snapshot(directory):
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_text())
    payloads = []
    for item in manifest['files']:
        path = directory/item['file']
        if path.parent != directory or path.suffix != '.json':
            raise ValueError('Invalid snapshot filename')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('Snapshot checksum mismatch')
        payloads.append(json.loads(raw))
    return manifest, payloads
