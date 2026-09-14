"""Pure analysis functions; importing this module never reads or writes files."""

from dataclasses import dataclass
import math

import pandas as pd

REQUIRED = ("fl_date", "dep_delay", "origin", "dest", "op_unique_carrier")
REASONS = ("carrier_delay", "weather_delay", "nas_delay", "security_delay", "late_aircraft_delay")


@dataclass
class AnalysisResult:
    tables: dict[str, pd.DataFrame]
    summary: dict
    departures: pd.DataFrame


def analyze(data: pd.DataFrame, *, min_flights: int = 500,
            min_route_flights: int = 300, late_threshold: float = 15) -> AnalysisResult:
    """Analyze complete departure records. Late means strictly > threshold minutes.

    The default preserves this project's historical convention. It is not an
    official BTS on-time statistic. Missing reason minutes remain unknown.
    """
    for name, value in (("min_flights", min_flights), ("min_route_flights", min_route_flights)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if not math.isfinite(late_threshold) or late_threshold < 0:
        raise ValueError("late_threshold must be finite and non-negative")
    missing = sorted(set(REQUIRED) - set(data.columns))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    if not data.columns.is_unique:
        raise ValueError("Duplicate column names are not supported")

    frame = data.copy(deep=True)
    frame["fl_date"] = pd.to_datetime(frame["fl_date"], errors="coerce", format="mixed", utc=True)
    frame["dep_delay"] = pd.to_numeric(frame["dep_delay"], errors="coerce")
    frame.loc[~frame["dep_delay"].map(lambda v: pd.notna(v) and math.isfinite(v)), "dep_delay"] = float("nan")
    for col in ("origin", "dest", "op_unique_carrier"):
        frame[col] = frame[col].astype("string").str.strip().replace("", pd.NA)
    if "cancelled" in frame:
        cancelled = pd.to_numeric(frame["cancelled"], errors="coerce").eq(1)
    else:
        cancelled = pd.Series(False, index=frame.index)
    invalid = frame[list(REQUIRED)].isna().any(axis=1)
    valid = frame.loc[~cancelled & ~invalid].copy()
    if valid.empty:
        raise ValueError("No valid departure records remain after excluding cancelled or incomplete rows")
    valid["month"] = valid["fl_date"].dt.strftime("%Y-%m")
    valid["day_of_week"] = valid["fl_date"].dt.dayofweek + 1
    valid["late_flag"] = valid["dep_delay"].gt(late_threshold)

    by_month = valid.groupby("month").agg(
        n=("dep_delay", "size"), avg_dep_delay=("dep_delay", "mean"), late_rate=("late_flag", "mean"))
    by_month["on_time_rate"] = 1 - by_month["late_rate"]

    def ranked(column: str) -> pd.DataFrame:
        table = valid.groupby(column).agg(n=("dep_delay", "size"), avg_dep_delay=("dep_delay", "mean"))
        return table.loc[table["n"] >= min_flights].sort_values("avg_dep_delay", ascending=False, kind="stable").head(15)

    routes = valid.groupby(["origin", "dest"]).agg(
        n=("dep_delay", "size"), late_rate=("late_flag", "mean"),
        avg_dep_delay=("dep_delay", "mean"), p90_dep_delay=("dep_delay", lambda s: s.quantile(.9)))
    routes = routes.loc[routes["n"] >= min_route_flights].sort_values(
        ["late_rate", "avg_dep_delay"], ascending=False, kind="stable").head(20)
    routes.index = pd.Index([f"{origin}-{dest}" for origin, dest in routes.index], name="route")

    # These fields describe reported delay reasons, often arrival-based. They
    # are not a causal decomposition of the departure delays calculated above.
    reason_records = []
    for reason in REASONS:
        values = pd.to_numeric(valid[reason], errors="coerce") if reason in valid else pd.Series(float("nan"), index=valid.index)
        known = values.map(lambda v: pd.notna(v) and math.isfinite(v) and v >= 0)
        reason_records.append({"reason": reason, "minutes_total": values.loc[known].sum() if known.any() else float("nan"),
                               "observed_rows": int(known.sum()), "missing_or_invalid_rows": int((~known).sum())})
    reasons = pd.DataFrame(reason_records).set_index("reason")
    total = reasons["minutes_total"].sum(min_count=1)
    reasons["share"] = reasons["minutes_total"] / total if pd.notna(total) and total > 0 else float("nan")
    reasons = reasons[["share", "minutes_total", "observed_rows", "missing_or_invalid_rows"]]
    tables = {"by_month_metrics": by_month, "worst_origins": ranked("origin"),
              "worst_carriers": ranked("op_unique_carrier"), "top_risky_routes": routes,
              "delay_reason_share": reasons}
    warnings = []
    for name in ("worst_origins", "worst_carriers", "top_risky_routes"):
        if tables[name].empty:
            warnings.append(f"{name}: no group meets the minimum flight count; CSV contains headers only")
    if reasons["missing_or_invalid_rows"].sum() > 0:
        warnings.append("Reason coverage is incomplete; blank values mean unknown, not zero")
    if pd.isna(total) or total <= 0:
        warnings.append("No positive reported reason minutes; reason shares are undefined")
    summary = {"input_rows": len(data), "analyzed_rows": len(valid),
               "cancelled_rows_excluded": int(cancelled.sum()),
               "invalid_non_cancelled_rows_excluded": int((invalid & ~cancelled).sum()),
               "late_threshold_minutes": late_threshold, "late_comparison": ">",
               "min_flights": min_flights, "min_route_flights": min_route_flights,
               "late_rate": float(valid["late_flag"].mean()),
               "on_time_rate": float(1 - valid["late_flag"].mean()),
               "avg_dep_delay": float(valid["dep_delay"].mean()), "warnings": warnings}
    return AnalysisResult(tables, summary, valid)
