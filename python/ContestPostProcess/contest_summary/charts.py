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

def render_mode_pie(df, title, outdir, overwrite=False):
    """
    Pie chart showing QSO distribution by normalized mode category.
    """
    outfile = outdir / "mode_distribution.png"
    if not should_write_output(outfile, overwrite=overwrite):
        return

    required = {"MODE_NORM"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"render_mode_pie requires columns: {sorted(required)}; "
            f"missing {sorted(missing)}"
        )

    counts = df["MODE_NORM"].value_counts()

    mode_colors = {
        "CW": "#1f77b4",
        "PH": "#ff7f0e",
        "DIG": "#2ca02c",
        "Other": "#7f7f7f",
    }

    colors = [mode_colors.get(m, "#7f7f7f") for m in counts.index]

    plt.figure()
    counts.plot.pie(
        autopct="%1.1f%%",
        colors=colors,
    )

    plt.title(f"{title} — Mode Distribution")
    plt.ylabel("")

    plt.savefig(outfile, dpi=300, bbox_inches="tight")
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

def render_operator_qso_donut(df, title, outdir, overwrite=False):
    """
    Nested donut chart:
      inner ring = operator QSO totals
      outer ring = operator/mode QSO totals

    Requires:
      - OPERATOR_NORM column
      - MODE_NORM column
    """
    outfile = outdir / "operator_qso_distribution.png"
    if not should_write_output(outfile, overwrite=overwrite):
        return

    required = {"OPERATOR_NORM", "MODE_NORM"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"render_operator_qso_donut requires columns: {sorted(required)}; "
            f"missing {sorted(missing)}"
        )

    work = df.copy()
    work["OPERATOR_NORM"] = work["OPERATOR_NORM"].astype(str).str.strip()
    work["MODE_NORM"] = work["MODE_NORM"].astype(str).str.strip()

    inner_counts = (
        work.groupby("OPERATOR_NORM")
        .size()
        .sort_values(ascending=False)
    )

    outer_counts = (
        work.groupby(["OPERATOR_NORM", "MODE_NORM"])
        .size()
        .reset_index(name="count")
    )

    # Keep outer slices grouped in the same order as the inner ring.
    operator_order = list(inner_counts.index)
    mode_order = ["CW", "PH", "DIG", "Other"]

    outer_counts["operator_sort"] = outer_counts["OPERATOR_NORM"].apply(operator_order.index)

    outer_counts["mode_sort"] = outer_counts["MODE_NORM"].apply(
        lambda m: mode_order.index(m) if m in mode_order else len(mode_order)
    )

    outer_counts = outer_counts.sort_values(
        by=["operator_sort", "mode_sort", "MODE_NORM"]
    )

    mode_colors = {
        "CW": "#1f77b4",    # blue
        "PH": "#ff7f0e",    # orange
        "DIG": "#2ca02c",   # green
        "Other": "#7f7f7f"  # gray
    }

    outer_colors = [
        mode_colors.get(row.MODE_NORM, "#7f7f7f")
        for row in outer_counts.itertuples(index=False)
    ]

    inner_sizes = inner_counts.tolist()
    inner_labels = inner_counts.index.tolist()

    outer_sizes = outer_counts["count"].tolist()
    outer_labels = [
        f"{row.OPERATOR_NORM} {row.MODE_NORM}"
        for row in outer_counts.itertuples(index=False)
    ]

    fig, ax = plt.subplots(figsize=(10, 10))

    # Inner ring: operator totals
    ax.pie(
        inner_sizes,
        labels=inner_labels,
        radius=1.0,
        wedgeprops=dict(width=0.3, edgecolor="white"),
        autopct=lambda pct: f"{pct:.1f}%" if pct >= 4 else "",
        pctdistance=0.78,
        labeldistance=0.62,
    )

    # Outer ring: operator/mode totals
    ax.pie(
        outer_sizes,
        labels=None,
        colors=outer_colors,
        radius=1.3,
        wedgeprops=dict(width=0.3, edgecolor="white"),
        autopct=lambda pct: f"{pct:.1f}%" if pct >= 3 else "",
        pctdistance=0.88,
    )

    ax.set(aspect="equal")
    ax.set_title(f"{title} — QSOs by Operator (outer ring shows mode)")

    # Legend for outer ring slices
    from matplotlib.patches import Patch

    legend_handles = [
        Patch(facecolor=color, label=mode)
        for mode, color in mode_colors.items()
    ]

    ax.legend(
        handles=legend_handles,
        title="Mode",
        loc="center left",
        bbox_to_anchor=(1.0, 0.5)
    )

    plt.tight_layout()
    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)

def render_operator_time_donut(sessions_df, title, outdir, overwrite=False):
    """
    Nested donut chart:
      inner ring = operator credited time totals
      outer ring = operator/mode credited time totals

    Requires:
      - OPERATOR_NORM
      - MODE_NORM
      - credited_minutes
    """
    outfile = outdir / "operator_time_distribution.png"
    if not should_write_output(outfile, overwrite=overwrite):
        return

    required = {"OPERATOR_NORM", "MODE_NORM", "credited_minutes"}
    missing = required - set(sessions_df.columns)
    if missing:
        raise ValueError(
            f"render_operator_time_donut requires columns: {sorted(required)}; "
            f"missing {sorted(missing)}"
        )

    work = sessions_df.copy()
    work["OPERATOR_NORM"] = work["OPERATOR_NORM"].astype(str).str.strip()
    work["MODE_NORM"] = work["MODE_NORM"].astype(str).str.strip()

    inner_counts = (
        work.groupby("OPERATOR_NORM")["credited_minutes"]
        .sum()
        .sort_values(ascending=False)
    )

    outer_counts = (
        work.groupby(["OPERATOR_NORM", "MODE_NORM"])["credited_minutes"]
        .sum()
        .reset_index()
    )

    operator_order = list(inner_counts.index)
    mode_order = ["CW", "PH", "DIG", "Other"]

    outer_counts["operator_sort"] = outer_counts["OPERATOR_NORM"].apply(operator_order.index)
    outer_counts["mode_sort"] = outer_counts["MODE_NORM"].apply(
        lambda m: mode_order.index(m) if m in mode_order else len(mode_order)
    )
    outer_counts = outer_counts.sort_values(
        by=["operator_sort", "mode_sort", "MODE_NORM"]
    )

    mode_colors = {
        "CW": "#1f77b4",    # blue
        "PH": "#ff7f0e",    # orange
        "DIG": "#2ca02c",   # green
        "Other": "#7f7f7f", # gray
    }

    outer_colors = [
        mode_colors.get(row.MODE_NORM, "#7f7f7f")
        for row in outer_counts.itertuples(index=False)
    ]

    inner_sizes = inner_counts.tolist()
    inner_labels = inner_counts.index.tolist()

    outer_sizes = outer_counts["credited_minutes"].tolist()

    fig, ax = plt.subplots(figsize=(10, 10))

    def _autopct_minutes(total_minutes, min_pct=4):
        def inner(pct):
            if pct < min_pct:
                return ""
            minutes = total_minutes * pct / 100.0
            return f"{pct:.1f}%"
        return inner

    inner_total = sum(inner_sizes)
    outer_total = sum(outer_sizes)

    ax.pie(
        inner_sizes,
        labels=inner_labels,
        radius=1.0,
        wedgeprops=dict(width=0.3, edgecolor="white"),
        autopct=_autopct_minutes(inner_total, min_pct=4),
        pctdistance=0.78,
        labeldistance=0.62,
    )

    ax.pie(
        outer_sizes,
        labels=None,
        colors=outer_colors,
        radius=1.3,
        wedgeprops=dict(width=0.3, edgecolor="white"),
        autopct=_autopct_minutes(outer_total, min_pct=3),
        pctdistance=0.88,
    )

    from matplotlib.patches import Patch

    legend_handles = [
        Patch(facecolor=color, label=mode)
        for mode, color in mode_colors.items()
    ]

    ax.legend(
        handles=legend_handles,
        title="Mode",
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
    )

    ax.set(aspect="equal")
    ax.set_title(f"{title} — Operating Time by Operator (outer ring shows mode)")

    plt.tight_layout()
    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)

