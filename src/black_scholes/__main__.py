import argparse
import json
from dataclasses import asdict
from . import Inputs, price, greeks, implied_volatility


def main():
    p = argparse.ArgumentParser(description="European Black–Scholes–Merton analytics")
    for name, default in (("spot",100),("strike",100),("maturity",1),("rate",0.05),("volatility",0.2),("dividend",0)):
        p.add_argument("--" + name, type=float, default=default)
    p.add_argument("--kind", choices=["call", "put"], default="call")
    p.add_argument("--market-price", type=float)
    p.add_argument("--method", choices=["newton", "bisection"], default="newton")
    args = vars(p.parse_args())
    target, method = args.pop("market_price"), args.pop("method")
    x = Inputs(**args)
    out = {"inputs": asdict(x), "price": price(x)}
    if x.maturity > 0 and x.volatility > 0:
        out["greeks_raw"] = asdict(greeks(x))
    if target is not None:
        out["implied_volatility"] = asdict(implied_volatility(target, x, method))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
