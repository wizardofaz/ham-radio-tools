import json
from importlib import resources


_DXCC_TABLE = None


def load_dxcc_table():
    """
    Load the shipped DXCC lookup table once.
    """
    global _DXCC_TABLE

    if _DXCC_TABLE is not None:
        return _DXCC_TABLE

    with resources.files("contest_summary.data").joinpath("dxcc_table.json").open(
        "r", encoding="utf-8"
    ) as f:
        _DXCC_TABLE = json.load(f)

    return _DXCC_TABLE


def continent_from_dxcc(dxcc):
    if not dxcc:
        return None

    table = load_dxcc_table()

    entry = table.get(str(dxcc))
    if not entry:
        return None

    return entry.get("continent")