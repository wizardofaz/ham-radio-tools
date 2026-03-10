def write_summary(df, stats, title, outdir):

    outfile = outdir / "summary.txt"

    with open(outfile, "w") as f:

        f.write(title + "\n\n")

        f.write(f"QSOs: {len(df)}\n")

        f.write("\nBand counts:\n")
        for band, count in df["BAND"].value_counts().items():
            f.write(f"{band}: {count}\n")