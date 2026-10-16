# Market data and reproducibility

The historical study uses a Yahoo Finance SPY option-chain snapshot captured on
24 September 2026 through yfinance. Original provider response files and cookie
caches are not distributed. No redistribution license for provider data is granted.

The screened quote table in `results/spy-market-surface/accepted_quotes.csv` and
its `summary.json` are the inputs to the offline Heston comparison. The other
CSV/HTML files are research outputs. Input hashes and calibration settings are
recorded in `results/heston-comparison/summary.json`.

To acquire a new snapshot, from the repository root after installation:

```sh
python scripts/build_surface.py --symbol SPY
```

The command reports its output directory. To calibrate that new snapshot:

```sh
python scripts/compare_models.py --input results/surface-SPY-TIMESTAMP --output results/new-comparison
```

A new download will not reproduce the historical snapshot. Raw downloads stay
under the ignored `data/raw/` directory. To replay a snapshot you already hold:

```sh
python scripts/build_surface.py --snapshot data/raw/YOUR-SNAPSHOT --output results/replay
```

Quotes can be delayed, unavailable, or rate-limited. No replacement observations
are invented when retrieval fails. Synthetic fixtures used by unit tests are
separate from the saved empirical study.
