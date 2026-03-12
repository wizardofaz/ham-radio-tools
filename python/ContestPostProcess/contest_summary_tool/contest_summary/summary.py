from .output_control import should_write_output

def write_summary(df, stats, title, outdir, elapsed_seconds=None, overwrite=False):

    outfile = outdir / "summary.txt"
    if not should_write_output(outfile, overwrite=overwrite):
        return
    
    with open(outfile, "w") as f:
        f.write(title + "\n")
        f.write("=" * len(title) + "\n\n")

        f.write(f"Total QSOs: {len(df)}\n\n")

        if elapsed_seconds is not None:
            minutes = int(elapsed_seconds // 60)
            seconds = int(elapsed_seconds % 60)
            f.write(f"Elapsed time: {minutes} min {seconds} sec\n\n")

        f.write("Enrichment statistics\n")
        f.write("---------------------\n")
        f.write(f"Original QSOs: {stats['original']}\n")
        f.write(f"Filled from callsign reuse: {stats['filled_from_calls']}\n")
        f.write(f"Filled from grid inference: {stats['filled_from_grid']}\n")
        f.write(f"  US state: {stats['filled_from_grid_us_state']}\n")
        f.write(f"  VE province: {stats['filled_from_grid_ve_prov']}\n")
        f.write(f"Filled from QRZ lookup: {stats['filled_from_qrz']}\n")
        f.write(f"  STATE: {stats['filled_from_qrz_state']}\n")
        f.write(f"  VE_PROV: {stats['filled_from_qrz_ve_prov']}\n")
        f.write(f"  COUNTRY: {stats['filled_from_qrz_country']}\n")
        f.write(f"  GRIDSQUARE: {stats['filled_from_qrz_grid']}\n")

        f.write("\nQRZ details\n")
        f.write("-----------\n")
        f.write(f"Cache hits: {stats['qrz_cache_hits']}\n")
        f.write(f"Queries attempted: {stats['qrz_queries_attempted']}\n")
        f.write(f"Exact hits: {stats['qrz_exact_hits']}\n")
        f.write(f"Stripped-call hits: {stats['qrz_stripped_hits']}\n")
        f.write(f"Not found: {stats['qrz_not_found']}\n")
        f.write(f"Login retries: {stats['qrz_login_retries']}\n")

        f.write("\nScope\n")
        f.write("-----\n")
        f.write(f"US QSOs: {stats['qso_scope']['US_QSOS']}\n")
        f.write(f"Canada QSOs: {stats['qso_scope']['CANADA_QSOS']}\n")

        f.write("\nMissing after enrichment\n")
        f.write("------------------------\n")
        f.write(f"STATE (US only): {stats['missing_after']['STATE_US_ONLY']}\n")
        f.write(f"VE_PROV (Canada only): {stats['missing_after']['VE_PROV_CANADA_ONLY']}\n")
        f.write(f"COUNTRY: {stats['missing_after']['COUNTRY']}\n")
        f.write(f"GRIDSQUARE: {stats['missing_after']['GRIDSQUARE']}\n")
        f.write(f"CONT: {stats['missing_after']['CONT']}\n")

        f.write("\nBand counts\n")
        f.write("-----------\n")
        for band, count in df["BAND"].value_counts().items():
            f.write(f"{band}: {count}\n")

        f.write("\nContinent counts\n")
        f.write("----------------\n")
        if "CONT" in df:
            for cont, count in df["CONT"].value_counts().items():
                f.write(f"{cont}: {count}\n")