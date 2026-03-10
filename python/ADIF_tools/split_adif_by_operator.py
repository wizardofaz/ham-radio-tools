#!/usr/bin/env python3

import re
import sys
from pathlib import Path
from collections import defaultdict

OUTPUT_DIR = "split_by_operator"
UNKNOWN_OPERATOR = "_UNKNOWN"

GRID_RE = re.compile(r"^[A-R]{2}[0-9]{2}([A-X]{2}([0-9]{2})?)?$")
TAG_RE = re.compile(r"<([^>]+)>", re.IGNORECASE)

CALLSIGN_FIELDS = {
    "CALL",
    "OPERATOR",
    "STATION_CALLSIGN",
    "OWNER_CALLSIGN",
}


def normalize_callsign(v):
    if v is None:
        return None
    v = v.strip().upper()
    return v if v else None


def normalize_grid(v):
    if v is None:
        return None
    v = v.strip().upper()
    if not v:
        return None
    if len(v) < 4:
        return None
    if not GRID_RE.fullmatch(v):
        return None
    return v


def decode_input_bytes(path: Path) -> str:
    """
    Read raw bytes and require strict UTF-8.
    On failure, print a useful diagnostic and exit.
    """
    raw = path.read_bytes()

    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        start = max(0, e.start - 16)
        end = min(len(raw), e.end + 16)
        snippet = raw[start:end]

        hex_bytes = " ".join(f"{b:02X}" for b in snippet)

        # Best-effort preview for human diagnosis only.
        preview_cp1252 = snippet.decode("cp1252", errors="replace")
        preview_latin1 = snippet.decode("latin-1", errors="replace")

        print("\nError: input file is not valid UTF-8.\n", file=sys.stderr)
        print(f"File: {path}", file=sys.stderr)
        print(f"Decode failed at byte offset {e.start}.", file=sys.stderr)
        print(f"Reason: {e}", file=sys.stderr)
        print(file=sys.stderr)
        print(f"Nearby raw bytes [{start}:{end}]:", file=sys.stderr)
        print(f"  {hex_bytes}", file=sys.stderr)
        print(file=sys.stderr)
        print("Best-effort preview of nearby bytes:", file=sys.stderr)
        print(f"  cp1252 : {preview_cp1252}", file=sys.stderr)
        print(f"  latin-1: {preview_latin1}", file=sys.stderr)
        print(file=sys.stderr)
        print("No output files were written.", file=sys.stderr)
        sys.exit(1)


def parse_adif_records(body):
    records = []
    current = []
    pos = 0

    while True:
        m = TAG_RE.search(body, pos)
        if not m:
            trailing = body[pos:].strip()
            if trailing:
                raise ValueError("Unexpected trailing non-tag text after last ADIF field.")
            break

        pos = m.end()
        tag = m.group(1)
        parts = tag.split(":")
        name = parts[0].strip().upper()

        if name == "EOH":
            continue

        if name == "EOR":
            records.append(current)
            current = []
            continue

        if len(parts) < 2 or not parts[1].strip():
            raise ValueError(f"Invalid ADIF tag missing length: <{tag}>")

        try:
            length = int(parts[1].strip())
        except ValueError:
            raise ValueError(f"Invalid ADIF field length in tag: <{tag}>")

        if pos + length > len(body):
            raise ValueError(f"Field <{tag}> extends past end of file.")

        value = body[pos:pos + length]
        pos += length

        current.append((name, value))

    if current:
        records.append(current)

    return records


def get_field(record, name):
    name = name.upper()
    for f, v in reversed(record):
        if f == name:
            return v
    return None


def remove_field(record, name):
    name = name.upper()
    record[:] = [(f, v) for (f, v) in record if f != name]


def set_field(record, name, value):
    remove_field(record, name)
    record.append((name.upper(), value))


def record_to_text(record):
    out = []
    for f, v in record:
        out.append(f"<{f}:{len(v)}>{v}")
    out.append("<EOR>")
    return "\n".join(out) + "\n"


def safe_filename(s):
    s = s.strip().upper()
    s = s.replace("/", "_")
    s = re.sub(r'[<>:"\\|?*\x00-\x1F ]', "_", s)
    s = s.strip("._")
    return s or UNKNOWN_OPERATOR


def sort_key_for_record(record):
    return (
        get_field(record, "QSO_DATE") or "",
        get_field(record, "TIME_ON") or "",
        get_field(record, "CALL") or "",
    )


def main():
    if len(sys.argv) != 2:
        print("Usage: python split_adif_by_operator.py logfile.adi")
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    text = decode_input_bytes(path)

    eoh = re.search(r"<EOH>", text, re.IGNORECASE)
    if eoh:
        header = text[:eoh.end()]
        body = text[eoh.end():]
    else:
        header = "<EOH>"
        body = text

    try:
        records = parse_adif_records(body)
    except Exception as e:
        print(f"\nError parsing ADIF: {e}", file=sys.stderr)
        print("No output files were written.", file=sys.stderr)
        sys.exit(1)

    stats = {
        "total": 0,
        "inherit_op": 0,
        "inherit_station": 0,
    }

    grid_errors = []
    groups = defaultdict(list)

    for i, record in enumerate(records, start=1):
        stats["total"] += 1

        for field in CALLSIGN_FIELDS:
            v = get_field(record, field)
            if v is not None:
                v2 = normalize_callsign(v)
                remove_field(record, field)
                if v2 is not None:
                    record.append((field, v2))

        operator = normalize_callsign(get_field(record, "OPERATOR"))
        station = normalize_callsign(get_field(record, "STATION_CALLSIGN"))

        if operator is None and station is not None:
            operator = station
            stats["inherit_op"] += 1

        if station is None and operator is not None:
            station = operator
            stats["inherit_station"] += 1

        if operator is not None or station is not None:
            if operator is not None:
                set_field(record, "OPERATOR", operator)
            if station is not None:
                set_field(record, "STATION_CALLSIGN", station)
            # Ensure both are present if at least one existed.
            if operator is None:
                operator = station
                set_field(record, "OPERATOR", operator)
            if station is None:
                station = operator
                set_field(record, "STATION_CALLSIGN", station)
        else:
            operator = UNKNOWN_OPERATOR
            remove_field(record, "OPERATOR")
            remove_field(record, "STATION_CALLSIGN")

        grid_raw = get_field(record, "MY_GRIDSQUARE")
        grid = normalize_grid(grid_raw)

        if grid is None:
            grid_errors.append((i, grid_raw))
            continue

        set_field(record, "MY_GRIDSQUARE", grid)

        groups[(operator, grid)].append(record)

    if grid_errors:
        print(f"\nError: {len(grid_errors)} records failed MY_GRIDSQUARE validation.\n", file=sys.stderr)

        for rec_num, val in grid_errors[:20]:
            if val is None:
                detail = "missing"
            elif not val.strip():
                detail = "blank"
            else:
                detail = f"invalid value {val!r}"
            print(f"  Record {rec_num}: {detail}", file=sys.stderr)

        if len(grid_errors) > 20:
            print(f"  ... {len(grid_errors) - 20} more", file=sys.stderr)

        print("\nNo output files were written.", file=sys.stderr)
        sys.exit(1)

    outdir = path.parent / OUTPUT_DIR
    outdir.mkdir(exist_ok=True)

    summary = []

    for (op, grid), recs in sorted(groups.items()):
        recs.sort(key=sort_key_for_record)

        fname = f"{safe_filename(op)}_{grid}.adi"
        fpath = outdir / fname

        with open(fpath, "w", encoding="utf-8", newline="\n") as f:
            f.write(header)
            f.write("\n")
            for r in recs:
                f.write(record_to_text(r))
                f.write("\n")

        summary.append((op, grid, len(recs)))

    print(f"\nProcessed {stats['total']} records.\n")
    print("Per operator / grid output:")
    for op, grid, n in summary:
        print(f"  {op:10} {grid:8} {n}")

    print()
    print(
        f"Warning: {stats['inherit_op']} of {stats['total']} records "
        f"inherited OPERATOR from STATION_CALLSIGN"
    )
    print(
        f"Warning: {stats['inherit_station']} of {stats['total']} records "
        f"inherited STATION_CALLSIGN from OPERATOR"
    )
    print(f"\nOutput written to: {outdir}\n")


if __name__ == "__main__":
    main()