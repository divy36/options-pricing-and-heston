"""Run from the project root after installing the package, or with PYTHONPATH=src."""
import json
from black_scholes.benchmark import run

if __name__ == "__main__":
    summary = run("results")
    print(json.dumps(summary, indent=2))
    raise SystemExit(bool(summary["failed_comparisons"]))
