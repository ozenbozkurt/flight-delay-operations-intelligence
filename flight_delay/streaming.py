"""Memory-bounded CSV analysis."""

from __future__ import annotations

import math
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd

from .analysis import AnalysisResult, REASONS, REQUIRED


def _validate(
    *,
    min_flights: int,
    min_route_flights: int,
    late_threshold: float,
) -> None:
    for name, value in (
        ("min_flights", min_flights),
        ("min_route_flights", min_route_flights),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if not math.isfinite(late_threshold) or late_threshold < 0:
        raise ValueError("late_threshold must be finite and non-negative")


def _validate_columns(columns) -> None:
    missing = sorted(set(REQUIRED) - set(columns))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    if not pd.Index(columns).is_unique:
        raise ValueError("Duplicate column names are not supported")


def _clean_chunk(data: pd.DataFrame, late_threshold: float) -> tuple[pd.DataFrame, int, int, int]:
    frame = data.copy(deep=True)

    frame["fl_date"] = pd.to_datetime(
        frame["fl_date"], errors="coerce", format="mixed", utc=True
    )
    frame["dep_delay"] = pd.to_numeric(frame["dep_delay"], errors="coerce")
    frame.loc[
        ~frame["dep_delay"].map(
            lambda v: pd.notna(v) and math.isfinite(v)
        ),
        "dep_delay",
    ] = float("nan")

    for col in ("origin", "dest", "op_unique_carrier"):
        frame[col] = (
            frame[col]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    if "cancelled" in frame:
        cancelled = pd.to_numeric(
            frame["cancelled"], errors="coerce"
        ).eq(1)
    else:
        cancelled = pd.Series(False, index=frame.index)

    invalid = frame[list(REQUIRED)].isna().any(axis=1)
    valid = frame.loc[~cancelled & ~invalid].copy()

    if not valid.empty:
        valid["month"] = valid["fl_date"].dt.strftime("%Y-%m")
        valid["late_flag"] = valid["dep_delay"].gt(late_threshold)

    return (
        valid,
        int(cancelled.sum()),
        int((invalid & ~cancelled).sum()),
        len(valid),
    )


def _add_group_stats(state: dict, keys, frame: pd.DataFrame) -> None:
    grouped = frame.groupby(keys, sort=False)
    for key, group in grouped:
        if not isinstance(key, tuple):
            key = (key,)
        item = state.setdefault(key, [0, 0.0, 0])
        item[0] += len(group)
        item[1] += float(group["dep_delay"].sum())
        item[2] += int(group["late_flag"].sum())


def _ranked_table(state: dict, min_flights: int) -> pd.DataFrame:
    rows = []
    for key, (n, delay_sum, _) in state.items():
        rows.append(
            {
                "group": key[0],
                "n": n,
                "avg_dep_delay": delay_sum / n,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=["n", "avg_dep_delay"]
        ).rename_axis("group")

    table = pd.DataFrame(rows).set_index("group").sort_index()
    table.index = pd.Index(table.index, dtype="string", name="group")
    table = table.loc[table["n"] >= min_flights]
    return table.sort_values(
        "avg_dep_delay",
        ascending=False,
        kind="stable",
    ).head(15)


def _reason_stats(
    reason_state: dict[str, list[float | int]],
    observed_rows: int,
) -> pd.DataFrame:
    rows = []
    for reason in REASONS:
        total, observed = reason_state.get(reason, [float("nan"), 0])
        rows.append(
            {
                "reason": reason,
                "minutes_total": total,
                "observed_rows": int(observed),
                "missing_or_invalid_rows": observed_rows - int(observed),
            }
        )

    reasons = pd.DataFrame(rows).set_index("reason")
    total = reasons["minutes_total"].sum(min_count=1)
    reasons["share"] = (
        reasons["minutes_total"] / total
        if pd.notna(total) and total > 0
        else float("nan")
    )
    return reasons[
        ["share", "minutes_total", "observed_rows", "missing_or_invalid_rows"]
    ]


def _route_p90(
    input_path: Path,
    chunksize: int,
    qualifying_routes: set[tuple[str, str]],
) -> dict[tuple[str, str], float]:
    if not qualifying_routes:
        return {}

    result = {}

    with tempfile.TemporaryDirectory(prefix="flight-delay-p90-") as temp_dir:
        db_path = Path(temp_dir) / "route_delays.sqlite"
        conn = sqlite3.connect(db_path)

        try:
            conn.execute(
                """
                CREATE TABLE route_delays (
                    origin TEXT NOT NULL,
                    dest TEXT NOT NULL,
                    dep_delay REAL NOT NULL
                )
                """
            )

            for chunk in pd.read_csv(
                input_path,
                dtype=str,
                keep_default_na=False,
                chunksize=chunksize,
            ):
                valid, _, _, _ = _clean_chunk(chunk, late_threshold=0)

                if valid.empty:
                    continue

                pairs = pd.MultiIndex.from_arrays(
                    [valid["origin"], valid["dest"]]
                )
                selected = valid.loc[
                    pairs.isin(qualifying_routes),
                    ["origin", "dest", "dep_delay"],
                ]

                if selected.empty:
                    continue

                conn.executemany(
                    "INSERT INTO route_delays VALUES (?, ?, ?)",
                    selected.itertuples(index=False, name=None),
                )

            conn.commit()

            conn.execute(
                "CREATE INDEX idx_route_delay "
                "ON route_delays(origin, dest, dep_delay)"
            )

            for origin, dest in qualifying_routes:
                n = int(
                    conn.execute(
                        "SELECT COUNT(*) FROM route_delays "
                        "WHERE origin = ? AND dest = ?",
                        (origin, dest),
                    ).fetchone()[0]
                )

                if n == 0:
                    continue

                position = (n - 1) * 0.9
                lower = math.floor(position)
                upper = math.ceil(position)

                values = conn.execute(
                    "SELECT dep_delay FROM route_delays "
                    "WHERE origin = ? AND dest = ? "
                    "ORDER BY dep_delay "
                    "LIMIT ? OFFSET ?",
                    (origin, dest, upper - lower + 1, lower),
                ).fetchall()

                lower_value = float(values[0][0])
                upper_value = float(values[-1][0])

                result[(origin, dest)] = (
                    lower_value
                    + (upper_value - lower_value)
                    * (position - lower)
                )
        finally:
            conn.close()

    return result


def analyze_csv(
    input_path: Path,
    *,
    chunksize: int,
    min_flights: int = 500,
    min_route_flights: int = 300,
    late_threshold: float = 15,
) -> AnalysisResult:
    """Analyze a CSV incrementally while keeping only bounded-size chunks in RAM."""
    _validate(
        min_flights=min_flights,
        min_route_flights=min_route_flights,
        late_threshold=late_threshold,
    )
    if isinstance(chunksize, bool) or not isinstance(chunksize, int) or chunksize < 1:
        raise ValueError("chunksize must be a positive integer")

    header = pd.read_csv(
        input_path,
        dtype=str,
        keep_default_na=False,
        nrows=0,
    )
    _validate_columns(header.columns)

    input_rows = 0
    analyzed_rows = 0
    cancelled_rows = 0
    invalid_rows = 0
    delay_sum = 0.0
    late_count = 0

    month_state = {}
    origin_state = {}
    carrier_state = {}
    route_state = {}

    reason_state = {
        reason: [float("nan"), 0]
        for reason in REASONS
    }

    for chunk in pd.read_csv(
        input_path,
        dtype=str,
        keep_default_na=False,
        chunksize=chunksize,
    ):
        input_rows += len(chunk)

        valid, cancelled, invalid, analyzed = _clean_chunk(
            chunk, late_threshold
        )
        cancelled_rows += cancelled
        invalid_rows += invalid
        analyzed_rows += analyzed

        if valid.empty:
            continue

        delay_sum += float(valid["dep_delay"].sum())
        late_count += int(valid["late_flag"].sum())

        _add_group_stats(month_state, "month", valid)
        _add_group_stats(origin_state, "origin", valid)
        _add_group_stats(carrier_state, "op_unique_carrier", valid)
        _add_group_stats(route_state, ["origin", "dest"], valid)

        for reason in REASONS:
            if reason not in valid:
                reason_state[reason][1] += 0
                continue

            values = pd.to_numeric(valid[reason], errors="coerce")
            known = values.map(
                lambda v: pd.notna(v)
                and math.isfinite(v)
                and v >= 0
            )

            if known.any():
                if math.isnan(reason_state[reason][0]):
                    reason_state[reason][0] = 0.0
                reason_state[reason][0] += float(values.loc[known].sum())
                reason_state[reason][1] += int(known.sum())

    if analyzed_rows == 0:
        raise ValueError(
            "No valid departure records remain after excluding cancelled or incomplete rows"
        )

    month_rows = []
    for (month,), (n, total, late) in month_state.items():
        late_rate = late / n
        month_rows.append(
            {
                "month": month,
                "n": n,
                "avg_dep_delay": total / n,
                "late_rate": late_rate,
            }
        )

    by_month = (
        pd.DataFrame(month_rows)
        .set_index("month")
        .sort_index()
    )
    by_month["on_time_rate"] = 1 - by_month["late_rate"]

    origins = _ranked_table(origin_state, min_flights)
    origins.index.name = "origin"

    carriers = _ranked_table(carrier_state, min_flights)
    carriers.index.name = "op_unique_carrier"

    qualifying_routes = {
        key
        for key, (n, _, _) in route_state.items()
        if n >= min_route_flights
    }

    p90s = _route_p90(
        input_path,
        chunksize,
        qualifying_routes,
    )

    route_rows = []
    for (origin, dest), (n, total, late) in route_state.items():
        if n < min_route_flights:
            continue
        route_rows.append(
            {
                "origin": origin,
                "dest": dest,
                "n": n,
                "late_rate": late / n,
                "avg_dep_delay": total / n,
                "p90_dep_delay": p90s.get((origin, dest), float("nan")),
            }
        )

    routes = (
        pd.DataFrame(route_rows)
        .set_index(["origin", "dest"])
        .sort_index()
    )
    routes = routes.sort_values(
        ["late_rate", "avg_dep_delay"],
        ascending=False,
        kind="stable",
    ).head(20)
    routes.index = pd.Index(
        [f"{origin}-{dest}" for origin, dest in routes.index],
        name="route",
    )

    reasons = _reason_stats(reason_state, analyzed_rows)
    total_reason_minutes = reasons["minutes_total"].sum(min_count=1)

    warnings = []
    tables = {
        "by_month_metrics": by_month,
        "worst_origins": origins,
        "worst_carriers": carriers,
        "top_risky_routes": routes,
        "delay_reason_share": reasons,
    }

    for name in (
        "worst_origins",
        "worst_carriers",
        "top_risky_routes",
    ):
        if tables[name].empty:
            warnings.append(
                f"{name}: no group meets the minimum flight count; CSV contains headers only"
            )

    if reasons["missing_or_invalid_rows"].sum() > 0:
        warnings.append(
            "Reason coverage is incomplete; blank values mean unknown, not zero"
        )

    if pd.isna(total_reason_minutes) or total_reason_minutes <= 0:
        warnings.append(
            "No positive reported reason minutes; reason shares are undefined"
        )

    late_rate = late_count / analyzed_rows
    summary = {
        "input_rows": input_rows,
        "analyzed_rows": analyzed_rows,
        "cancelled_rows_excluded": cancelled_rows,
        "invalid_non_cancelled_rows_excluded": invalid_rows,
        "late_threshold_minutes": late_threshold,
        "late_comparison": ">",
        "min_flights": min_flights,
        "min_route_flights": min_route_flights,
        "late_rate": float(late_rate),
        "on_time_rate": float(1 - late_rate),
        "avg_dep_delay": float(delay_sum / analyzed_rows),
        "warnings": warnings,
    }

    return AnalysisResult(
        tables=tables,
        summary=summary,
        departures=pd.DataFrame(),
    )
