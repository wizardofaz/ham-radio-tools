import time
from pathlib import Path

from .cli import parse_args
from .adif_utils import load_adif
from .enrich import enrich_records
from .charts import render_band_pie, render_continent_pie
from .maps import render_map
from .summary import write_summary


def main():
    start_time = time.time()

    args = parse_args()

    adif_path = Path(args.adif)

    if args.outdir:
        outdir = Path(args.outdir)
    else:
        outdir = adif_path.parent

    outdir.mkdir(parents=True, exist_ok=True)

    title = args.title if args.title else adif_path.stem
    qrz_cache_path = outdir / "qrz_cache.json"

    print("Loading ADIF...")
    df = load_adif(adif_path)

    print("Enriching records...")
    df, stats = enrich_records(
        df,
        use_qrz=args.qrz,
        qrz_cache_path=qrz_cache_path,
    )

    print("Generating charts...")
    render_band_pie(df, title, outdir)
    render_continent_pie(df, title, outdir)

    print("Generating map...")
    render_map(df, title, outdir, args)

    print("\nEnrichment statistics:")
    print(f"  QSOs loaded: {stats['original']}")
    print(f"  Filled from callsign reuse: {stats['filled_from_calls']}")
    print(f"  Filled from grid inference: {stats['filled_from_grid']}")
    print(f"    US state: {stats['filled_from_grid_us_state']}")
    print(f"    VE province: {stats['filled_from_grid_ve_prov']}")
    print(f"  Filled from QRZ lookup: {stats['filled_from_qrz']}")
    print(f"    STATE: {stats['filled_from_qrz_state']}")
    print(f"    VE_PROV: {stats['filled_from_qrz_ve_prov']}")
    print(f"    COUNTRY: {stats['filled_from_qrz_country']}")
    print(f"    GRIDSQUARE: {stats['filled_from_qrz_grid']}")
    print("  QRZ details:")
    print(f"    Cache hits: {stats['qrz_cache_hits']}")
    print(f"    Queries attempted: {stats['qrz_queries_attempted']}")
    print(f"    Exact hits: {stats['qrz_exact_hits']}")
    print(f"    Stripped-call hits: {stats['qrz_stripped_hits']}")
    print(f"    Not found: {stats['qrz_not_found']}")
    print(f"    Login retries: {stats['qrz_login_retries']}")
    print("  Scope:")
    print(f"    US QSOs: {stats['qso_scope']['US_QSOS']}")
    print(f"    Canada QSOs: {stats['qso_scope']['CANADA_QSOS']}")
    print("  Missing after enrichment:")
    print(f"    STATE (US only): {stats['missing_after']['STATE_US_ONLY']}")
    print(f"    VE_PROV (Canada only): {stats['missing_after']['VE_PROV_CANADA_ONLY']}")
    print(f"    COUNTRY: {stats['missing_after']['COUNTRY']}")
    print(f"    GRIDSQUARE: {stats['missing_after']['GRIDSQUARE']}")
    print(f"    CONT: {stats['missing_after']['CONT']}")

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    print(f"\nElapsed time: {minutes} min {seconds} sec")

    if args.summary:
        write_summary(df, stats, title, outdir, elapsed_seconds=elapsed)

    print("\nDone.")