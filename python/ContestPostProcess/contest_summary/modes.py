# contest_summary/modes.py

def normalize_mode(raw_mode: str, mode_categories: dict) -> str:
    """
    Map a raw ADIF MODE value into one of the configured categories.

    Returns one of the configured category keys, or 'Other' if no match.
    Matching is case-insensitive and ignores surrounding whitespace.
    """
    mode = (raw_mode or "").strip().upper()
    if not mode:
        return "Other"

    for category, members in mode_categories.items():
        for member in members:
            if mode == str(member).strip().upper():
                return category

    return "Other"


def normalize_mode_series(series, mode_categories: dict):
    """
    Normalize a pandas Series of raw MODE values.
    """
    return series.apply(lambda m: normalize_mode(m, mode_categories))