# Flight Delay Operations Intelligence

Turn a flight CSV into departure-delay metrics, airport/carrier rankings,
route risk tables, and optional charts. Run the included synthetic demo first,
then analyze your own data on Windows, macOS, or Linux.

This repository started as a U.S. 2024 aviation analytics case study. The new
`flight_delay` Python package makes the analysis reusable without editing
hard-coded paths or downloading a large dataset.

## Quickstart

Requires Python 3.10 or newer. From a local clone:

```sh
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```sh
# macOS / Linux
source .venv/bin/activate
```

Install and run:

```sh
python -m pip install ".[charts]"
flight-delay --input examples/demo_flights.csv --output demo-output --min-flights 1 --min-route-flights 1 --charts
```

Without activation on Windows, use `.\.venv\Scripts\python.exe -m pip install ".[charts]"`
and `.\.venv\Scripts\python.exe -m flight_delay` with the same arguments.
For CSV/JSON output only, install with `python -m pip install .` and omit `--charts`.
This is a local package installation; no PyPI publication is claimed.

The demo should report **7 analyzed flights from 8 rows**, with one cancellation
excluded and a late rate of **3/7 (42.86%)**. These are synthetic examples, not
actual airline performance. See [demo data notes](examples/README.md).

## Analyze your data

```sh
flight-delay --input path/to/flights.csv --output my-results --charts
```

The output directory must be new or empty, protecting previous results. Paths
are relative to your current directory; absolute paths work too. Quote paths
containing spaces. The command returns exit code 2 with an error message for
invalid inputs. A failed write can leave partial outputs; rerun in a new folder.

| Option | Default | Meaning |
| --- | --- | --- |
| `--min-flights` | 500 | Minimum analyzed rows per origin/carrier ranking |
| `--min-route-flights` | 300 | Minimum analyzed rows per route ranking |
| `--late-threshold` | 15 | A departure is late if delay is **strictly greater** than this many minutes |
| `--charts` | off | Generate four PNGs using the optional Matplotlib dependency |

Use small minimum counts only for demonstrations. Rankings from a handful of
observations should not be treated as reliable operational comparisons.

## CSV schema and metric definitions

Each row represents one flight. Required columns:

| Column | Meaning |
| --- | --- |
| `fl_date` | Flight date, preferably `YYYY-MM-DD` |
| `dep_delay` | Departure delay in minutes; negative values are valid early departures |
| `origin`, `dest` | Non-empty airport identifiers |
| `op_unique_carrier` | Non-empty operating carrier identifier |

Optional fields: `cancelled` (`1` means cancelled), `carrier_delay`,
`weather_delay`, `nas_delay`, `security_delay`, `late_aircraft_delay`.
All other columns are ignored. Weekday is derived from the date. Dates with
 timezone offsets are normalized to UTC; use date-only values for local flight dates.

- Rows with invalid dates, non-finite/missing delay, or missing identifiers are
  excluded. Cancellations flagged `1` are excluded even if they have a delay.
- One complete-record population is used across the new CLI's departure metrics.
  `summary.json` records input, analyzed, cancelled, and other excluded row counts.
- Delays of exactly 15 minutes count as on-time under the default historical
  project convention. These outputs are **not official BTS on-time statistics**.
- Reported reason minutes are summed over the analyzed flights. Unknown,
  negative, or non-finite reason values are not imputed to zero. Coverage counts
  accompany each reason; shares are blank when there is no positive total.
- Reason fields may describe arrival delays. Their shares are not a causal
  decomposition of departure delay and should be interpreted separately.
- Early departures remain negative in averages. Samples are not reweighted;
  month-balanced samples do not automatically represent annual traffic totals.
- The CLI reads the input into memory. For very large files, prepare a suitable
  sample first; automatic streaming analysis is not implemented.

## Outputs

| File | Contents |
| --- | --- |
| `summary.json` | Parameters, row accounting, overall metrics, and warnings |
| `by_month_metrics.csv` | Counts, average departure delay, late/on-time rates |
| `worst_origins.csv` | Top 15 qualifying origins by average departure delay |
| `worst_carriers.csv` | Top 15 qualifying carriers by average departure delay |
| `top_risky_routes.csv` | Top 20 qualifying routes by late rate, then average delay |
| `delay_reason_share.csv` | Reported reason minutes, shares, and coverage |

With `--charts`, the CLI also writes `avg_delay_by_month.png`,
`late_rate_by_month.png`, `dep_delay_hist.png`, and `avg_delay_by_dayofweek.png`.
Groups below the minimum produce a header-only CSV and a warning, not a crash.

## Python API

```python
import pandas as pd
from flight_delay import analyze

data = pd.read_csv("examples/demo_flights.csv", dtype=str, keep_default_na=False)
result = analyze(data, min_flights=1, min_route_flights=1)
print(result.summary)
print(result.tables["top_risky_routes"])
```

`analyze` does not modify the input DataFrame or write files.

## Tests and contributions

```sh
python -m pip install -e ".[charts]"
python -m unittest discover -s tests -v
```

The test suite covers known metrics, threshold boundaries, cancellations,
missing/invalid data, small groups, CLI output protection, and optional charts.
GitHub Actions is configured to run tests on Windows/Linux and Python 3.10/3.12.
See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change.

## Historical case study

[REPORT.md](REPORT.md), the tracked `outputs/`, and the original scripts
(`analysis.py`, `analysis_eda.py`, `analysis_ops.py`, `main.py`, `run.ps1`) are
retained as the original case study. Use the new CLI for reusable analysis.
Its complete-record population and reason handling differ from the older
scripts; previously published numbers have not been regenerated or replaced.

![Historical sample: average departure delay by month](outputs/avg_delay_by_month.png)

## Release status

The source code, synthetic examples, and repository documentation are licensed
under the [MIT License](LICENSE). Version 0.1.0 is a local development package;
it has not been published to PyPI.

The existing historical `data/` CSV files are not covered by the MIT License.
Their original retrieval record is unavailable, so use the official BTS source
for new work and see [DATA_SOURCES.md](DATA_SOURCES.md) for the reuse boundary.
Those historical datasets are excluded from the wheel and source distribution.
