import pandas as pd

from .geo_infer import infer_admin1_from_grid


FIELDS_TO_REUSE = ["STATE", "VE_PROV", "COUNTRY", "GRIDSQUARE", "CONT"]


def is_missing(value):
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def clean_value(value):
    if is_missing(value):
        return None
    if isinstance(value, str):
        return value.strip()
    return value


def is_us_qso(row):
    country = clean_value(row.get("COUNTRY"))
    dxcc = clean_value(row.get("DXCC"))

    if country in {"United States", "United States of America", "USA", "U.S.A."}:
        return True
    if dxcc == "291":
        return True
    return False


def is_canada_qso(row):
    country = clean_value(row.get("COUNTRY"))
    dxcc = clean_value(row.get("DXCC"))

    if country == "Canada":
        return True
    if dxcc == "1":
        return True
    return False


def count_missing_where(df, field, predicate):
    if field not in df.columns:
        return sum(1 for _, row in df.iterrows() if predicate(row))

    count = 0
    for _, row in df.iterrows():
        if predicate(row) and is_missing(row.get(field)):
            count += 1
    return count


def count_missing(df, field):
    if field not in df.columns:
        return len(df)
    return sum(is_missing(v) for v in df[field])


def enrich_records(df, use_qrz=False):
    stats = {
        "original": len(df),
        "filled_from_calls": 0,
        "filled_from_grid": 0,
        "filled_from_grid_us_state": 0,
        "filled_from_grid_ve_prov": 0,
        "filled_from_qrz": 0,
    }

    # Normalize fields we care about
    for field in ["CALL", "DXCC"] + FIELDS_TO_REUSE:
        if field not in df.columns:
            df[field] = None
        df[field] = df[field].apply(clean_value)

    # Build best-known info by callsign
    call_info = {}

    for _, row in df.iterrows():
        call = clean_value(row.get("CALL"))
        if not call:
            continue

        info = call_info.setdefault(call, {})

        for field in FIELDS_TO_REUSE:
            val = clean_value(row.get(field))
            if val is not None and field not in info:
                info[field] = val

    # Fill missing fields from same-call info
    for idx, row in df.iterrows():
        call = clean_value(row.get("CALL"))
        if not call or call not in call_info:
            continue

        info = call_info[call]

        for field in FIELDS_TO_REUSE:
            current_val = clean_value(row.get(field))
            if current_val is None and field in info:
                df.at[idx, field] = info[field]
                stats["filled_from_calls"] += 1

    # Grid-based inference:
    # - use grid-6 directly when available
    # - otherwise use grid-4
    # - accept only if exactly one target admin-1 polygon intersects the box
    # - if ambiguous, leave unresolved for QRZ later
    for idx, row in df.iterrows():
        grid = clean_value(row.get("GRIDSQUARE"))
        if not grid:
            continue

        inferred = infer_admin1_from_grid(grid)
        if not inferred:
            continue

        # US state
        if inferred["country_code"] == "US" and is_missing(row.get("STATE")):
            df.at[idx, "STATE"] = inferred["admin1_abbrev"]
            if is_missing(row.get("COUNTRY")):
                df.at[idx, "COUNTRY"] = "United States of America"
            stats["filled_from_grid"] += 1
            stats["filled_from_grid_us_state"] += 1
            continue

        # Canada province
        if inferred["country_code"] == "CA" and is_missing(row.get("VE_PROV")):
            df.at[idx, "VE_PROV"] = inferred["admin1_abbrev"]
            if is_missing(row.get("COUNTRY")):
                df.at[idx, "COUNTRY"] = "Canada"
            stats["filled_from_grid"] += 1
            stats["filled_from_grid_ve_prov"] += 1
            continue

        # Leave Mexico and other inferred admin-1 results unused for now.
        # They are still useful as ambiguity blockers because infer_admin1_from_grid()
        # returns None when the box intersects multiple target polygons.

    stats["missing_after"] = {
        "STATE_US_ONLY": count_missing_where(df, "STATE", is_us_qso),
        "VE_PROV_CANADA_ONLY": count_missing_where(df, "VE_PROV", is_canada_qso),
        "COUNTRY": count_missing(df, "COUNTRY"),
        "GRIDSQUARE": count_missing(df, "GRIDSQUARE"),
        "CONT": count_missing(df, "CONT"),
    }

    stats["qso_scope"] = {
        "US_QSOS": sum(1 for _, row in df.iterrows() if is_us_qso(row)),
        "CANADA_QSOS": sum(1 for _, row in df.iterrows() if is_canada_qso(row)),
    }

    return df, stats