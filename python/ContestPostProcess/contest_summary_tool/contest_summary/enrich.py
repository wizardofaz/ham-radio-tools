import pandas as pd

from .geo_infer import infer_admin1_from_grid
from .qrz_lookup import QRZLookupClient


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


def normalize_qrz_country(country):
    country = clean_value(country)
    if not country:
        return None

    mapping = {
        "USA": "United States of America",
        "United States": "United States of America",
        "U.S.A.": "United States of America",
        "Canada": "Canada",
        "Mexico": "Mexico",
    }
    return mapping.get(country, country)


def normalize_qrz_canada_prov(state_value):
    state_value = clean_value(state_value)
    if not state_value:
        return None

    mapping = {
        "AB": "AB", "ALBERTA": "AB",
        "BC": "BC", "BRITISH COLUMBIA": "BC",
        "MB": "MB", "MANITOBA": "MB",
        "NB": "NB", "NEW BRUNSWICK": "NB",
        "NL": "NL", "NEWFOUNDLAND AND LABRADOR": "NL",
        "NS": "NS", "NOVA SCOTIA": "NS",
        "NT": "NT", "NORTHWEST TERRITORIES": "NT",
        "NU": "NU", "NUNAVUT": "NU",
        "ON": "ON", "ONTARIO": "ON",
        "PE": "PE", "PRINCE EDWARD ISLAND": "PE",
        "QC": "QC", "QUEBEC": "QC", "PQ": "QC",
        "SK": "SK", "SASKATCHEWAN": "SK",
        "YT": "YT", "YUKON": "YT",
    }
    return mapping.get(state_value.upper())


def enrich_records(df, use_qrz=False, qrz_cache_path=None):
    stats = {
        "original": len(df),
        "filled_from_calls": 0,
        "filled_from_grid": 0,
        "filled_from_grid_us_state": 0,
        "filled_from_grid_ve_prov": 0,
        "filled_from_qrz": 0,
        "filled_from_qrz_state": 0,
        "filled_from_qrz_ve_prov": 0,
        "filled_from_qrz_country": 0,
        "filled_from_qrz_grid": 0,
        "qrz_cache_hits": 0,
        "qrz_queries_attempted": 0,
        "qrz_exact_hits": 0,
        "qrz_stripped_hits": 0,
        "qrz_not_found": 0,
        "qrz_login_retries": 0,
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

    # Grid-based inference
    for idx, row in df.iterrows():
        grid = clean_value(row.get("GRIDSQUARE"))
        if not grid:
            continue

        inferred = infer_admin1_from_grid(grid)
        if not inferred:
            continue

        if inferred["country_code"] == "US" and is_missing(row.get("STATE")):
            df.at[idx, "STATE"] = inferred["admin1_abbrev"]
            if is_missing(row.get("COUNTRY")):
                df.at[idx, "COUNTRY"] = "United States of America"
            stats["filled_from_grid"] += 1
            stats["filled_from_grid_us_state"] += 1
            continue

        if inferred["country_code"] == "CA" and is_missing(row.get("VE_PROV")):
            df.at[idx, "VE_PROV"] = inferred["admin1_abbrev"]
            if is_missing(row.get("COUNTRY")):
                df.at[idx, "COUNTRY"] = "Canada"
            stats["filled_from_grid"] += 1
            stats["filled_from_grid_ve_prov"] += 1
            continue

    # QRZ fallback
    qrz_client = None
    if use_qrz:
        cache_path = qrz_cache_path or "qrz_cache.json"
        qrz_client = QRZLookupClient(cache_path=cache_path)

        if not qrz_client.enabled():
            print("Warning: QRZ requested, but QRZ_USERNAME / QRZ_PASSWORD are not set.")
            qrz_client = None

    if qrz_client:
        for idx, row in df.iterrows():
            call = clean_value(row.get("CALL"))
            if not call:
                continue

            needs_state = is_us_qso(row) and is_missing(row.get("STATE"))
            needs_ve_prov = is_canada_qso(row) and is_missing(row.get("VE_PROV"))
            needs_country = is_missing(row.get("COUNTRY"))
            needs_grid = is_missing(row.get("GRIDSQUARE"))

            if not (needs_state or needs_ve_prov or needs_country or needs_grid):
                continue

            try:
                result = qrz_client.lookup(call)
            except Exception as e:
                print(f"Warning: QRZ lookup failed for {call}: {e}")
                continue

            if not result or not result.get("found"):
                continue

            qrz_country = normalize_qrz_country(result.get("country"))
            qrz_state = clean_value(result.get("state"))
            qrz_grid = clean_value(result.get("grid"))

            filled_any = False

            if needs_country and qrz_country:
                df.at[idx, "COUNTRY"] = qrz_country
                stats["filled_from_qrz"] += 1
                stats["filled_from_qrz_country"] += 1
                filled_any = True

            # US state
            if is_missing(row.get("STATE")):
                target_country = clean_value(df.at[idx, "COUNTRY"])
                if target_country in {"United States", "United States of America", "USA", "U.S.A."}:
                    if qrz_state:
                        df.at[idx, "STATE"] = qrz_state.upper()
                        stats["filled_from_qrz"] += 1
                        stats["filled_from_qrz_state"] += 1
                        filled_any = True

            # Canada province
            if is_missing(row.get("VE_PROV")):
                target_country = clean_value(df.at[idx, "COUNTRY"])
                if target_country == "Canada":
                    prov = normalize_qrz_canada_prov(qrz_state)
                    if prov:
                        df.at[idx, "VE_PROV"] = prov
                        stats["filled_from_qrz"] += 1
                        stats["filled_from_qrz_ve_prov"] += 1
                        filled_any = True

            # Grid
            if needs_grid and qrz_grid:
                df.at[idx, "GRIDSQUARE"] = qrz_grid.upper()
                stats["filled_from_qrz"] += 1
                stats["filled_from_qrz_grid"] += 1
                filled_any = True

        qrz_client.save_cache()
        stats["qrz_cache_hits"] = qrz_client.stats["qrz_cache_hits"]
        stats["qrz_queries_attempted"] = qrz_client.stats["qrz_queries_attempted"]
        stats["qrz_exact_hits"] = qrz_client.stats["qrz_exact_hits"]
        stats["qrz_stripped_hits"] = qrz_client.stats["qrz_stripped_hits"]
        stats["qrz_not_found"] = qrz_client.stats["qrz_not_found"]
        stats["qrz_login_retries"] = qrz_client.stats["qrz_login_retries"]

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