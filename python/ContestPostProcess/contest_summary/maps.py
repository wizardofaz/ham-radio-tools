from functools import lru_cache

import geopandas as gpd
import matplotlib.pyplot as plt

from .geo_infer import load_admin1
from .output_control import should_write_output

ADMIN0_SOURCE = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"

US_NAMES = {"United States", "United States of America", "USA", "U.S.A."}
CANADA_NAMES = {"Canada"}
MEXICO_NAMES = {"Mexico"}
NA_EXCLUDE = US_NAMES | CANADA_NAMES | MEXICO_NAMES


@lru_cache(maxsize=1)
def load_admin0():
    world = gpd.read_file(ADMIN0_SOURCE)
    world = world.to_crs("EPSG:4326")

    # Normalize the country name column to "name"
    for col in ["ADMIN", "NAME", "name"]:
        if col in world.columns:
            if col != "name":
                world = world.rename(columns={col: "name"})
            break

    if "name" not in world.columns:
        raise RuntimeError(f"Could not find country name column in admin0 data: {list(world.columns)}")

    return world


def _safe_values(series):
    return {str(x).strip() for x in series.dropna() if str(x).strip()}


FIFTY_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}


def _us_states_worked(df):
    states = _safe_values(df.loc[df["STATE"].notna(), "STATE"])
    return states & FIFTY_STATES


def _ve_provs_worked(df):
    return _safe_values(df.loc[df["VE_PROV"].notna(), "VE_PROV"])


LOWER48 = FIFTY_STATES - {"AK", "HI"}


def _dx_countries_worked(df):
    dx = set()
    for _, row in df.iterrows():
        country = str(row.get("COUNTRY") or "").strip()
        state = str(row.get("STATE") or "").strip()

        # Canada never counts as DX here
        if country in CANADA_NAMES:
            continue

        # Lower 48 never counts as DX
        if country in US_NAMES and state in LOWER48:
            continue

        if country:
            dx.add(country)

    return dx


def _fig_ax(title, subtitle):
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.suptitle(title, fontsize=18, y=0.97)
    ax.set_title(subtitle, fontsize=11, pad=8)
    ax.set_axis_off()
    return fig, ax


def render_map(df, title, outdir, args, overwrite=False):
    if args.map == "countries" or args.map == "all":
        render_countries_map(df, title, outdir, include_lower48=args.include_lower48, overwrite=overwrite)
    elif args.map == "states_dx" or args.map == "all":
        render_states_dx_map(df, title, outdir, overwrite=overwrite)
    elif args.map == "na_states_dx" or args.map == "all":
        render_na_states_dx_map(df, title, outdir, overwrite=overwrite)
    else:
        raise ValueError(f"Unknown map mode: {args.map}")


def render_countries_map(df, title, outdir, include_lower48=False, overwrite=False):
    outfile = outdir / "countries_map.png"
    if not should_write_output(outfile, overwrite=overwrite):
        return

    world = load_admin0().copy()
    worked = _safe_values(df.loc[df["COUNTRY"].notna(), "COUNTRY"])

    # Normalize a few common names to Natural Earth admin-0 names
    name_map = {
        "United States": "United States of America",
        "USA": "United States of America",
        "U.S.A.": "United States of America",
    }
    worked_names = {name_map.get(c, c) for c in worked}

    if not include_lower48:
        worked_names.discard("United States of America")

    world["worked"] = world["name"].isin(worked_names)

    qso_count = len(df)
    country_count = len(worked)

    fig, ax = _fig_ax(
        title,
        f"Worked countries • {qso_count} QSOs • {country_count} countries/entities in log",
    )
    world.plot(ax=ax, color="#efefef", edgecolor="0.55", linewidth=0.5)
    world[world["worked"]].plot(ax=ax, color="#4c78a8", edgecolor="0.35", linewidth=0.6)
    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)


def render_states_dx_map(df, title, outdir, overwrite=False):
    outfile = outdir / "states_dx_map.png"
    if not should_write_output(outfile, overwrite=overwrite):
        return

    world = load_admin0().copy()
    admin1 = load_admin1().copy()

    us_states = _us_states_worked(df)
    ve_provs = _ve_provs_worked(df)
    dx_countries = _dx_countries_worked(df)

    us_admin1 = admin1[
        (admin1["country_name"] == "United States of America")
        & (admin1["postal"].isin(us_states))
    ].copy()

    ca_admin1 = admin1[
        (admin1["country_name"] == "Canada")
        & (admin1["postal"].isin(ve_provs))
    ].copy()

    world["worked_dx"] = world["name"].isin(dx_countries)

    fig, ax = _fig_ax(
        title,
        f"US states + VE provinces + non-NA DX • "
        f"{len(us_states)} US states • {len(ve_provs)} VE provinces • {len(dx_countries)} DX countries",
    )

    # Base world
    world.plot(ax=ax, color="#f2f2f2", edgecolor="0.65", linewidth=0.4)

    # DX countries
    if len(world[world["worked_dx"]]) > 0:
        world[world["worked_dx"]].plot(ax=ax, color="#f2c14e", edgecolor="0.45", linewidth=0.5)

    # US worked states
    if len(us_admin1) > 0:
        us_admin1.plot(ax=ax, color="#4c78a8", edgecolor="0.25", linewidth=0.6)

    # Canada worked provinces
    if len(ca_admin1) > 0:
        ca_admin1.plot(ax=ax, color="#59a14f", edgecolor="0.25", linewidth=0.6)

    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)


def render_na_states_dx_map(df, title, outdir, overwrite=False):
    outfile = outdir / "na_states_dx_map.png"
    if not should_write_output(outfile, overwrite=overwrite):
        return

    world = load_admin0().copy()
    admin1 = load_admin1().copy()

    us_states = _us_states_worked(df)
    ve_provs = _ve_provs_worked(df)
    dx_countries = _dx_countries_worked(df)

    us_admin1 = admin1[
        (admin1["country_name"] == "United States of America")
        & (admin1["postal"].isin(us_states))
    ].copy()

    ca_admin1 = admin1[
        (admin1["country_name"] == "Canada")
        & (admin1["postal"].isin(ve_provs))
    ].copy()

    # Keep just North America base countries for context
    na_world = world[
        world["name"].isin({"United States of America", "Canada", "Mexico", "Greenland"})
    ].copy()

    fig, ax = _fig_ax(
        title,
        f"North America view • {len(us_states)} US states • {len(ve_provs)} VE provinces • "
        f"{len(dx_countries)} non-NA DX countries also worked",
    )

    na_world.plot(ax=ax, color="#f2f2f2", edgecolor="0.55", linewidth=0.5)

    if len(us_admin1) > 0:
        us_admin1.plot(ax=ax, color="#4c78a8", edgecolor="0.25", linewidth=0.6)

    if len(ca_admin1) > 0:
        ca_admin1.plot(ax=ax, color="#59a14f", edgecolor="0.25", linewidth=0.6)

    # North America framing
    ax.set_xlim(-170, -45)
    ax.set_ylim(5, 85)

    # Small note for DX count
    ax.text(
        -167,
        8,
        f"Also worked {len(dx_countries)} non-NA DX countries",
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="0.6"),
    )

    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)