# contest_summary/sessions.py

from datetime import datetime
import pandas as pd


def _normalize_time_on(value) -> str:
    """
    Normalize ADIF TIME_ON into hhmmss.

    Accepts values like:
      930   -> 093000
      0930  -> 093000
      093015 -> 093015
    """
    text = str(value or "").strip()
    if not text:
        raise ValueError("Missing TIME_ON value while building sessions.")

    digits = "".join(ch for ch in text if ch.isdigit())

    if len(digits) == 4:
        return digits + "00"
    if len(digits) == 6:
        return digits
    if len(digits) == 3:
        return "0" + digits + "00"
    if len(digits) == 5:
        return "0" + digits

    raise ValueError(f"Unsupported TIME_ON format: {value!r}")


def _build_timestamp(row) -> datetime:
    qso_date = str(row.get("QSO_DATE") or "").strip()
    if not qso_date:
        raise ValueError("Missing QSO_DATE value while building sessions.")

    time_on = _normalize_time_on(row.get("TIME_ON"))
    return datetime.strptime(qso_date + time_on, "%Y%m%d%H%M%S")


def add_qso_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of df with QSO_TS datetime column added.
    """
    out = df.copy()
    out["QSO_TS"] = out.apply(_build_timestamp, axis=1)
    return out


def _finalize_session(session_rows, min_session_minutes: float):
    """
    Build one finalized session dict from a list of row dicts.
    """
    start_ts = session_rows[0]["QSO_TS"]
    end_ts = session_rows[-1]["QSO_TS"]
    actual_minutes = (end_ts - start_ts).total_seconds() / 60.0
    credited_minutes = max(actual_minutes, min_session_minutes)

    return {
        "OPERATOR_NORM": session_rows[0]["OPERATOR_NORM"],
        "MODE_NORM": session_rows[0]["MODE_NORM"],
        "session_start": start_ts,
        "session_end": end_ts,
        "qso_count": len(session_rows),
        "actual_minutes": actual_minutes,
        "credited_minutes": credited_minutes,
    }


def _build_sessions_for_operator(
    op_df: pd.DataFrame,
    gap_minutes: float,
    min_session_minutes: float,
):
    """
    Build sessions for one operator only.

    New session when:
      - gap from previous QSO > gap_minutes
      - MODE_NORM changes
    """
    op_df = op_df.sort_values("QSO_TS").copy()
    rows = op_df.to_dict("records")

    if not rows:
        return []

    sessions = []
    current_session = [rows[0]]

    for row in rows[1:]:
        prev = current_session[-1]
        gap = (row["QSO_TS"] - prev["QSO_TS"]).total_seconds() / 60.0
        mode_changed = row["MODE_NORM"] != prev["MODE_NORM"]

        if gap > gap_minutes or mode_changed:
            sessions.append(
                _finalize_session(current_session, min_session_minutes)
            )
            current_session = [row]
        else:
            current_session.append(row)

    sessions.append(_finalize_session(current_session, min_session_minutes))
    return sessions


def build_sessions(df: pd.DataFrame, gap_minutes: float) -> pd.DataFrame:
    """
    Build a session dataframe from QSO records.

    Required columns:
      - OPERATOR_NORM
      - MODE_NORM
      - QSO_DATE
      - TIME_ON

    Returns a dataframe with one row per session.
    """
    required = {"OPERATOR_NORM", "MODE_NORM", "QSO_DATE", "TIME_ON"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"build_sessions requires columns: {sorted(required)}; "
            f"missing {sorted(missing)}"
        )

    work = add_qso_timestamp(df)
    min_session_minutes = gap_minutes / 2.0

    all_sessions = []
    for operator, op_df in work.groupby("OPERATOR_NORM", sort=True):
        operator_sessions = _build_sessions_for_operator(
            op_df,
            gap_minutes=gap_minutes,
            min_session_minutes=min_session_minutes,
        )
        all_sessions.extend(operator_sessions)

    sessions_df = pd.DataFrame(all_sessions)

    if not sessions_df.empty:
        sessions_df = sessions_df.sort_values(
            ["OPERATOR_NORM", "session_start", "MODE_NORM"]
        ).reset_index(drop=True)

    return sessions_df