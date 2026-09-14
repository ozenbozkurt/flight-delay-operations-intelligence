"""Command-line entry point with explicit input/output paths."""

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

from . import __version__
from .analysis import analyze


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Analyze flight departure delays from a CSV.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--input", type=Path, required=True, help="Flight CSV; see README for required columns")
    p.add_argument("--output", type=Path, default=Path("analysis-output"), help="New or empty directory (default: analysis-output)")
    p.add_argument("--min-flights", type=int, default=500, help="Minimum rows per origin/carrier (default: 500)")
    p.add_argument("--min-route-flights", type=int, default=300, help="Minimum rows per route (default: 300)")
    p.add_argument("--late-threshold", type=float, default=15, help="Late means delay strictly greater than this number (default: 15)")
    p.add_argument("--charts", action="store_true", help="Also generate PNG charts; requires the charts extra")
    return p


def write_charts(result, output: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    month = result.tables["by_month_metrics"]
    for column, filename, title, ylabel, scale in (
        ("avg_dep_delay", "avg_delay_by_month", "Average departure delay", "Minutes", 1),
        ("late_rate", "late_rate_by_month", "Departure late rate", "Percent", 100),
    ):
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(month.index, month[column] * scale, marker="o")
        ax.set(title=title, xlabel="Month", ylabel=ylabel)
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()
        fig.savefig(output / f"{filename}.png", dpi=150)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(result.departures["dep_delay"], bins=60)
    ax.set(title="Departure delay distribution", xlabel="Minutes", ylabel="Flight count")
    fig.tight_layout()
    fig.savefig(output / "dep_delay_hist.png", dpi=150)
    plt.close(fig)
    days = result.departures.groupby("day_of_week")["dep_delay"].mean()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(days.index, days.values, marker="o")
    ax.set(title="Average departure delay by weekday", xlabel="Weekday (1=Monday, 7=Sunday)", ylabel="Minutes")
    fig.tight_layout()
    fig.savefig(output / "avg_delay_by_dayofweek.png", dpi=150)
    plt.close(fig)


def main(argv=None) -> int:
    p = parser()
    args = p.parse_args(argv)
    try:
        if args.output.exists() and (not args.output.is_dir() or any(args.output.iterdir())):
            raise ValueError("Output must be a new or empty directory; choose a different --output path")
        if args.charts:
            try:
                import matplotlib  # noqa: F401
            except ImportError as exc:
                raise ValueError('Charts require installation with: python -m pip install ".[charts]"') from exc
        data = pd.read_csv(args.input, dtype=str, keep_default_na=False)
        result = analyze(data, min_flights=args.min_flights, min_route_flights=args.min_route_flights,
                         late_threshold=args.late_threshold)
        result.summary["input_file"] = str(args.input)
        result.summary["tool_version"] = __version__
        args.output.mkdir(parents=True, exist_ok=True)
        for name, table in result.tables.items():
            table.to_csv(args.output / f"{name}.csv")
        (args.output / "summary.json").write_text(json.dumps(result.summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        if args.charts:
            write_charts(result, args.output)
        print(f"Analyzed {result.summary['analyzed_rows']} of {len(data)} rows. Output: {args.output}")
        for warning in result.summary["warnings"]:
            print(f"Warning: {warning}", file=sys.stderr)
        return 0
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
