import matplotlib.pyplot as plt

from .output_control import should_write_output


def render_band_pie(df, title, outdir, overwrite=False):
    outfile = outdir / "band_distribution.png"
    if not should_write_output(outfile, overwrite=overwrite):
        return

    counts = df["BAND"].value_counts()
    plt.figure()
    counts.plot.pie(autopct="%1.1f%%")
    plt.title(f"{title} — Band Distribution")
    plt.savefig(outfile)
    plt.close()


def render_continent_pie(df, title, outdir, overwrite=False):
    outfile = outdir / "continent_distribution.png"
    if not should_write_output(outfile, overwrite=overwrite):
        return

    counts = df["CONT"].value_counts()
    plt.figure()
    counts.plot.pie(autopct="%1.1f%%")
    plt.title(f"{title} — Continent Distribution")
    plt.savefig(outfile)
    plt.close()