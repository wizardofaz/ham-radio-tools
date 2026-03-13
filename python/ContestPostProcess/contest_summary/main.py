import time
from pathlib import Path

from .config import load_config, apply_cli_overrides
from .cli import parse_args
from .adif_utils import load_adif
from .enrich import enrich_records
from .charts import render_band_pie, render_continent_pie
from .maps import render_map
from .summary import write_summary
from .operators import add_operator_column
from .sessions import build_sessions
from .modes import normalize_mode_series

from .charts import (
    render_band_pie,
    render_continent_pie,
    render_operator_qso_donut,
    render_operator_time_donut,
)

def main():
    start_time = time.time()

    args = parse_args()
    adif_path = Path(args.adif)

    if args.outdir:
        outdir = Path(args.outdir)
    else:
        outdir = adif_path.parent
    outdir.mkdir(parents=True, exist_ok=True)
    
    config = load_config(args.config)
    config = apply_cli_overrides(config, args)

    gap_minutes = config["session_gap_minutes"]
    min_session_minutes = gap_minutes / 2
    mode_categories = config["mode_categories"]

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

    df = add_operator_column(df)
    df["MODE_NORM"] = normalize_mode_series(df["MODE"], mode_categories)
    sessions_df = build_sessions(df, gap_minutes)
    
    
    print("Generating charts...")
    render_band_pie(df, title, outdir, overwrite=args.overwrite)
    render_continent_pie(df, title, outdir, overwrite=args.overwrite)
    render_operator_qso_donut(df, title, outdir, overwrite=args.overwrite)
    render_operator_time_donut(sessions_df, title, outdir, overwrite=args.overwrite)

    print("Generating map...")
    render_map(df, title, outdir, args, overwrite=args.overwrite)

    print("\nEnrichment statistics:")
    print(f" QSOs loaded: {stats['original']}")
    print(f" Filled from callsign reuse: {stats['filled_from_calls']}")
    print(f" Filled from grid inference: {stats['filled_from_grid']}")
    print(f" US state: {stats['filled_from_grid_us_state']}")
    print(f" VE province: {stats['filled_from_grid_ve_prov']}")
    print(f" Filled from QRZ lookup: {stats['filled_from_qrz']}")
    print(f" STATE: {stats['filled_from_qrz_state']}")
    print(f" VE_PROV: {stats['filled_from_qrz_ve_prov']}")
    print(f" COUNTRY: {stats['filled_from_qrz_country']}")
    print(f" GRIDSQUARE: {stats['filled_from_qrz_grid']}")
    print(" QRZ details:")
    print(f" Cache hits: {stats['qrz_cache_hits']}")
    print(f" Queries attempted: {stats['qrz_queries_attempted']}")
    print(f" Exact hits: {stats['qrz_exact_hits']}")
    print(f" Stripped-call hits: {stats['qrz_stripped_hits']}")
    print(f" Not found: {stats['qrz_not_found']}")
    print(f" Login retries: {stats['qrz_login_retries']}")
    print(" Scope:")
    print(f" US QSOs: {stats['qso_scope']['US_QSOS']}")
    print(f" Canada QSOs: {stats['qso_scope']['CANADA_QSOS']}")
    print(" Missing after enrichment:")
    print(f" STATE (US only): {stats['missing_after']['STATE_US_ONLY']}")
    print(f" VE_PROV (Canada only): {stats['missing_after']['VE_PROV_CANADA_ONLY']}")
    print(f" COUNTRY: {stats['missing_after']['COUNTRY']}")
    print(f" GRIDSQUARE: {stats['missing_after']['GRIDSQUARE']}")
    print(f" CONT: {stats['missing_after']['CONT']}")

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    print(f"\nElapsed time: {minutes} min {seconds} sec")

    if args.summary:
        write_summary(
            df,
            stats,
            title,
            outdir,
            elapsed_seconds=elapsed,
            overwrite=args.overwrite,
        )

    print("\nDone.")