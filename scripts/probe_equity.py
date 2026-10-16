import yfinance as yf
from pathlib import Path
import json
cache = Path('data/cache'); cache.mkdir(parents=True, exist_ok=True)
yf.set_tz_cache_location(str(cache))
t = yf.Ticker('SPY')
print(t.options)
c = t.option_chain(t.options[5])
print(c.underlying)
print(c.calls[['contractSymbol','strike','bid','ask']].head().to_string())
