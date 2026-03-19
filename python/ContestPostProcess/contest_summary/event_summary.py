from datetime import datetime, timedelta, timezone
import math
import pandas as pd


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

US_NAMES = {
    "UNITED STATES", "UNITED STATES OF AMERICA", "USA", "U.S.A.", "US", "U.S."
}
CANADA_NAMES = {"CANADA", "CA"}

NULL_LIKE = {"", "NONE", "NAN", "NULL", "UNKNOWN"}


def norm_text(value):
    """Normalize a text field for distinct-count use."""
    if pd.isna(value):
        return None
    s = str(value).strip().upper()
    return None if s in NULL_LIKE else s


def pct(part, whole):
    return 0.0 if whole == 0 else 100.0 * part / whole


def ensure_utc_datetime(df):
    """
    Return a copy of df with a reliable UTC timestamp column named QSO_DT.
    Expects QSO_DATE and TIME_ON columns if QSO_DT does not already exist.
    """
    out = df.copy()

    if "QSO_DT" in out.columns and pd.api.types.is_datetime64_any_dtype(out["QSO_DT"]):
        return out

    if "QSO_DATE" not in out.columns or "TIME_ON" not in out.columns:
        raise ValueError("Need either QSO_DT or both QSO_DATE and TIME_ON columns.")

    date_str = out["QSO_DATE"].astype(str).str.strip()
    time_str = (
        out["TIME_ON"]
        .astype(str)
        .str.strip()
        .str.replace(r"\D", "", regex=True)
        .str.zfill(6)
        .str[:6]
    )

    out["QSO_DT"] = pd.to_datetime(
        date_str + time_str,
        format="%Y%m%d%H%M%S",
        errors="coerce",
        utc=True,
    )

    return out


def floor_to_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)


def iter_event_hours(start_dt, end_dt):
    """
    Yield hourly bucket starts from start_dt through end_dt inclusive by hour.
    Both arguments must be timezone-aware UTC datetimes.
    """
    current = floor_to_hour(start_dt)
    last = floor_to_hour(end_dt)
    while current <= last:
        yield current
        current += timedelta(hours=1)


def is_prime_hour(hour_dt):
    """
    Prime hours:
      1200z-2359z and 0000z-0459z
    Overnight:
      0500z-1159z
    """
    h = hour_dt.hour
    return (0 <= h <= 4) or (12 <= h <= 23)


def sessionize_operator_hours(
    df,
    operator_col="OPERATOR",
    dt_col="QSO_DT",
    gap_minutes=30,
    minimum_session_minutes=None,
):
    """
    Sum session durations across all operators.

    Session rule:
    - per operator, sort QSOs by time
    - new session when gap > gap_minutes
    - session duration = last - first
    - optional minimum_session_minutes floor per session
    """
    if minimum_session_minutes is None:
        minimum_session_minutes = gap_minutes / 2.0

    total_hours = 0.0

    work = df[[operator_col, dt_col]].copy()
    work[operator_col] = work[operator_col].map(norm_text)
    work = work.dropna(subset=[operator_col, dt_col]).sort_values([operator_col, dt_col])

    for op, group in work.groupby(operator_col):
        times = list(group[dt_col])
        if not times:
            continue

        session_start = times[0]
        prev = times[0]

        for t in times[1:]:
            gap = (t - prev).total_seconds() / 60.0
            if gap > gap_minutes:
                dur_min = (prev - session_start).total_seconds() / 60.0
                dur_min = max(dur_min, minimum_session_minutes)
                total_hours += dur_min / 60.0
                session_start = t
            prev = t

        dur_min = (prev - session_start).total_seconds() / 60.0
        dur_min = max(dur_min, minimum_session_minutes)
        total_hours += dur_min / 60.0

    return total_hours


def distinct_nonempty(series):
    vals = series.map(norm_text).dropna()
    return set(vals)


def count_geography(df):
    """
    Assumes your enriched dataframe already contains trustworthy geography.
    Preferred columns:
      US state:      STATE
      VE province:   PROVINCE
      Entity/country: COUNTRY or DXCC_NAME
    Adjust these names if your script uses different columns.
    """
    states = set()
    provinces = set()
    dx_entities = set()

    if "STATE" in df.columns:
        states = distinct_nonempty(df["STATE"])

    if "PROVINCE" in df.columns:
        provinces = distinct_nonempty(df["PROVINCE"])

    entity_col = None
    for candidate in ("COUNTRY", "DXCC_NAME"):
        if candidate in df.columns:
            entity_col = candidate
            break

    if entity_col is not None:
        for entity in distinct_nonempty(df[entity_col]):
            if entity not in US_NAMES and entity not in CANADA_NAMES:
                dx_entities.add(entity)

    return len(states), len(provinces), len(dx_entities)


def compute_event_summary(
    df,
    gap_minutes=30,
    minimum_session_minutes=None,
):
    """
    Compute the expanded numerical event summary.

    event_start_utc / event_end_utc:
      timezone-aware UTC datetimes
    """
    work = ensure_utc_datetime(df)

    # TODO take this from a config or CLI option
    event_start_utc = work["QSO_DT"].min().to_pydatetime()
    event_end_utc   = work["QSO_DT"].max().to_pydatetime()

    # Basic counts
    qso_count = len(work)

    unique_callsigns = 0
    if "CALL" in work.columns:
        unique_callsigns = len(distinct_nonempty(work["CALL"]))

    operator_count = 0
    if "OPERATOR" in work.columns:
        operator_count = len(distinct_nonempty(work["OPERATOR"]))

    # Operator hours
    operator_hours = sessionize_operator_hours(
        work,
        operator_col="OPERATOR",
        dt_col="QSO_DT",
        gap_minutes=gap_minutes,
        minimum_session_minutes=minimum_session_minutes,
    )

    # Coverage by hour
    qso_hours = set(
        floor_to_hour(ts.to_pydatetime())
        for ts in work["QSO_DT"].dropna()
    )

    all_hours = list(iter_event_hours(event_start_utc, event_end_utc))
    prime_hours = [h for h in all_hours if is_prime_hour(h)]
    overnight_hours = [h for h in all_hours if not is_prime_hour(h)]

    covered_all = sum(1 for h in all_hours if h in qso_hours)
    covered_prime = sum(1 for h in prime_hours if h in qso_hours)
    covered_overnight = sum(1 for h in overnight_hours if h in qso_hours)

    coverage_overall = pct(covered_all, len(all_hours))
    coverage_prime = pct(covered_prime, len(prime_hours))
    coverage_overnight = pct(covered_overnight, len(overnight_hours))

    # Geography
    states_count, provinces_count, dx_entities_count = count_geography(work)

    return {
        "qso_count": qso_count,
        "unique_callsigns": unique_callsigns,
        "operator_count": operator_count,
        "operator_hours": operator_hours,
        "coverage_overall": coverage_overall,
        "coverage_prime": coverage_prime,
        "coverage_overnight": coverage_overnight,
        "states_count": states_count,
        "provinces_count": provinces_count,
        "dx_entities_count": dx_entities_count,
    }


import os

def write_event_summary(summary, outdir):
    os.makedirs(outdir, exist_ok=True)

    outfile = os.path.join(outdir, "event_summary.txt")

    lines = [
        "Summary",
        "-------",
        f"QSOs: {summary['qso_count']}",
        f"Unique callsigns: {summary['unique_callsigns']}",
        "",
        f"Operators: {summary['operator_count']}",
        f"Operator hours: {summary['operator_hours']:.1f}",
        "",
        f"Coverage: {summary['coverage_overall']:.1f}% overall",
        f"Coverage prime: {summary['coverage_prime']:.1f}%",
        f"Coverage overnight: {summary['coverage_overnight']:.1f}%",
        "",
        f"States: {summary['states_count']}",
        f"Provinces: {summary['provinces_count']}",
        f"DX entities: {summary['dx_entities_count']}",
        "",
    ]

    with open(outfile, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Summary written to: {outfile}")
        