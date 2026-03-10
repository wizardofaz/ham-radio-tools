def enrich_records(df, use_qrz=False):

    stats = {
        "original": len(df),
        "filled_from_calls": 0,
        "filled_from_grid": 0,
        "filled_from_qrz": 0,
    }

    # Build lookup table for each callsign

    call_info = {}

    for _, row in df.iterrows():

        call = row.get("CALL")

        if not call:
            continue

        info = call_info.setdefault(call, {})

        for field in ["STATE", "VE_PROV", "COUNTRY", "GRIDSQUARE", "CONT"]:

            val = row.get(field)

            if val and field not in info:
                info[field] = val

    # Second pass: fill missing fields

    for idx, row in df.iterrows():

        call = row.get("CALL")

        if call not in call_info:
            continue

        info = call_info[call]

        for field in ["STATE", "VE_PROV", "COUNTRY", "GRIDSQUARE", "CONT"]:

            if not row.get(field) and field in info:

                df.at[idx, field] = info[field]

                stats["filled_from_calls"] += 1

    return df, stats