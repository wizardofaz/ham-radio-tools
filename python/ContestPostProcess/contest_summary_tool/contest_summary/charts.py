import matplotlib.pyplot as plt


def render_band_pie(df, title, outdir):

    counts = df["BAND"].value_counts()

    plt.figure()
    counts.plot.pie(autopct="%1.1f%%")

    plt.title(f"{title} — Band Distribution")

    outfile = outdir / "band_distribution.png"

    plt.savefig(outfile)
    plt.close()


def render_continent_pie(df, title, outdir):

    counts = df["CONT"].value_counts()

    plt.figure()
    counts.plot.pie(autopct="%1.1f%%")

    plt.title(f"{title} — Continent Distribution")

    outfile = outdir / "continent_distribution.png"

    plt.savefig(outfile)
    plt.close()