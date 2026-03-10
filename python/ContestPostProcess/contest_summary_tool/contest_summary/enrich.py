import pandas as pd


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

    if country in {"United States", "USA", "U.S.A."}:
        return True

    # Common ADIF DXCC for lower-48 USA
    if dxcc == "291":
        return True

    return False


def is_canada_qso(row):
    country = clean_value(row.get("COUNTRY"))
    dxcc = clean_value(row.get("DXCC"))

    if country == "Canada":
        return True

    # Common ADIF DXCC for Canada
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

    # Relevance-aware missing counts
    stats["missing_after"] = {
        "STATE_US_ONLY": count_missing_where(df, "STATE", is_us_qso),
        "VE_PROV_CANADA_ONLY": count_missing_where(df, "VE_PROV", is_canada_qso),
        "COUNTRY": count_missing(df, "COUNTRY"),
        "GRIDSQUARE": count_missing(df, "GRIDSQUARE"),
        "CONT": count_missing(df, "CONT"),
    }

    # Useful context counts
    stats["qso_scope"] = {
        "US_QSOS": sum(1 for _, row in df.iterrows() if is_us_qso(row)),
        "CANADA_QSOS": sum(1 for _, row in df.iterrows() if is_canada_qso(row)),
    }

    return df, stats