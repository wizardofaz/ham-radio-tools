from pathlib import Path

from .cli import parse_args
from .adif_utils import load_adif
from .enrich import enrich_records
from .charts import render_band_pie, render_continent_pie
from .maps import render_map
from .summary import write_summary


def main():
    args = parse_args()

    adif_path = Path(args.adif)

    if args.outdir:
        outdir = Path(args.outdir)
    else:
        outdir = adif_path.parent

    outdir.mkdir(parents=True, exist_ok=True)

    title = args.title if args.title else adif_path.stem

    print("Loading ADIF...")
    df = load_adif(adif_path)

    print("Enriching records...")
    df, stats = enrich_records(df, use_qrz=args.qrz)

    print("Generating charts...")
    render_band_pie(df, title, outdir)
    render_continent_pie(df, title, outdir)

    print("Generating map...")
    render_map(df, title, outdir, args)

    print("\nEnrichment statistics:")
    print(f"  QSOs loaded: {stats['original']}")
    print(f"  Filled from callsign reuse: {stats['filled_from_calls']}")
    print(f"  Filled from grid inference: {stats['filled_from_grid']}")
    print(f"  Filled from QRZ lookup: {stats['filled_from_qrz']}")

    if args.summary:
        write_summary(df, stats, title, outdir)

    print("\nDone.")
    
