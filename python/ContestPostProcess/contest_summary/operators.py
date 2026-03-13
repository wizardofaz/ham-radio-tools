# contest_summary/operators.py

import pandas as pd


def pick_operator(row) -> str:
    """
    Choose the operator identifier for one QSO row using this precedence:

        1. OPERATOR
        2. STATION_CALLSIGN
        3. OWNER_CALLSIGN

    Returns a normalized uppercase string.

    Raises ValueError if none of those fields are present and non-empty.
    """
    for field in ("OPERATOR", "STATION_CALLSIGN", "OWNER_CALLSIGN"):
        value = row.get(field)
        if pd.notna(value):
            text = str(value).strip().upper()
            if text:
                return text

    raise ValueError(
        "Could not determine operator for one or more QSOs. "
        "Need OPERATOR, STATION_CALLSIGN, or OWNER_CALLSIGN."
    )


def add_operator_column(df):
    """
    Return a copy of df with a normalized OPERATOR_NORM column added.
    """
    out = df.copy()
    out["OPERATOR_NORM"] = out.apply(pick_operator, axis=1)
    return out