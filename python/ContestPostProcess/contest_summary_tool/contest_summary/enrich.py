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
    for field in ["CALL"] + FIELDS_TO_REUSE:
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

    stats["missing_after"] = {
        "STATE": count_missing(df, "STATE"),
        "VE_PROV": count_missing(df, "VE_PROV"),
        "COUNTRY": count_missing(df, "COUNTRY"),
        "GRIDSQUARE": count_missing(df, "GRIDSQUARE"),
        "CONT": count_missing(df, "CONT"),
    }

    return df, stats