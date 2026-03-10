def write_summary(df, stats, title, outdir):

    outfile = outdir / "summary.txt"

    with open(outfile, "w") as f:

        f.write(title + "\n")
        f.write("=" * len(title) + "\n\n")

        f.write(f"Total QSOs: {len(df)}\n\n")

        f.write("Enrichment statistics\n")
        f.write("---------------------\n")

        f.write(f"Original QSOs: {stats['original']}\n")
        f.write(f"Filled from callsign reuse: {stats['filled_from_calls']}\n")
        f.write(f"Filled from grid inference: {stats['filled_from_grid']}\n")
        f.write(f"Filled from QRZ lookup: {stats['filled_from_qrz']}\n")

        f.write("\nBand counts\n")
        f.write("-----------\n")

        for band, count in df["BAND"].value_counts().items():
            f.write(f"{band}: {count}\n")

        f.write("\nContinent counts\n")
        f.write("----------------\n")

        if "CONT" in df:
            for cont, count in df["CONT"].value_counts().items():
                f.write(f"{cont}: {count}\n")