import re
import pandas as pd


def load_adif(path):
    """
    Minimal ADIF parser.

    Reads an ADIF file and returns a pandas DataFrame with
    uppercase field names.
    """

    with open(path, "r", errors="ignore") as f:
        text = f.read()

    # Split records
    records = re.split(r"<eor>", text, flags=re.IGNORECASE)

    rows = []

    field_pattern = re.compile(r"<(\w+):(\d+)>([^<]*)", re.IGNORECASE)

    for rec in records:

        fields = {}

        for match in field_pattern.finditer(rec):
            name = match.group(1).upper()
            value = match.group(3).strip()

            fields[name] = value

        if fields:
            rows.append(fields)

    df = pd.DataFrame(rows)

    return df