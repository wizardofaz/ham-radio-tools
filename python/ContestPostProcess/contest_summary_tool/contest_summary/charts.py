import matplotlib.pyplot as plt


def _save_chart(outfile, overwrite=False):
    if outfile.exists():
        if not overwrite:
            print(f"WARNING: Chart already exists, skipping: {outfile}")
            return False
        print(f"Overwriting existing chart: {outfile}")

    plt.savefig(outfile)
    return True


def render_band_pie(df, title, outdir, overwrite=False):
    counts = df["BAND"].value_counts()
    plt.figure()
    counts.plot.pie(autopct="%1.1f%%")
    plt.title(f"{title} — Band Distribution")
    outfile = outdir / "band_distribution.png"
    _save_chart(outfile, overwrite=overwrite)
    plt.close()


def render_continent_pie(df, title, outdir, overwrite=False):
    counts = df["CONT"].value_counts()
    plt.figure()
    counts.plot.pie(autopct="%1.1f%%")
    plt.title(f"{title} — Continent Distribution")
    outfile = outdir / "continent_distribution.png"
    _save_chart(outfile, overwrite=overwrite)
    plt.close()