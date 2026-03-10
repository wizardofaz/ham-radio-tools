#!/usr/bin/env python3

"""
Generate:
  1) Band distribution pie chart
  2) Continent distribution pie chart
  3) Colored world map of countries worked

Designed for contest-summary use from an ADIF file.

Requirements:
    pip install matplotlib geopandas pandas shapely pyogrio fiona

Optional:
    pip install adif_io

Usage:
    python contest_summary_map.py "K7RST 2026 ARRL DX PH.adi"
"""

from __future__ import annotations

import sys
import re
from pathlib import Path
from collections import Counter, defaultdict

import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd


# ----------------------------
# User-tweakable settings
# ----------------------------

TITLE = "RST WAS250-AZ Feb 25 to Mar 3 2026"
SUBTITLE_TEMPLATE = "Countries/territories worked • {qsos} QSOs • {dxcc} DXCC entities"

# Leave continental USA uncolored for ARRL DX
# EXCLUDE_LOWER_48 = True
EXCLUDE_LOWER_48 = False

# Worked-country color palette for adjacency coloring
PALETTE = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#17becf",  # cyan
]

BASEMAP_COLOR = "#eeeeee"
BASEMAP_EDGE = "0.4"

# Country-name fixes between ADIF COUNTRY and Natural Earth names
COUNTRY_NAME_MAP = {
    "Alaska": "United States of America",
    "Hawaii": "United States of America",
    "US Virgin Is.": "United States of America",
    "U.S. Virgin Is.": "United States of America",
    "Puerto Rico": "Puerto Rico",
    "Anguilla": "United Kingdom",
    "Aruba": "Netherlands",
    "Bonaire": "Netherlands",
    "Curacao": "Netherlands",
    "Curaçao": "Netherlands",
    "Azores": "Portugal",
    "Canary Is.": "Spain",
    "Cayman Is.": "United Kingdom",
    "Dominican Republic": "Dominican Rep.",
    "Bosnia-Herzegovina": "Bosnia and Herz.",
    "Czech Republic": "Czechia",
    "Trinidad & Tobago": "Trinidad and Tobago",
    "Asiatic Russia": "Russia",
}

# Manual repair for missing COUNTRY fields by callsign
CALLSIGN_COUNTRY_FIXES = {
    "JL3VUL/3": "Japan",
}


# ----------------------------
# ADIF parsing
# ----------------------------

def parse_adif_with_adif_io(path: Path) -> pd.DataFrame | None:
    try:
        import adif_io  # type: ignore
    except ImportError:
        return None

    try:
        qsos, _header = adif_io.read_from_file(str(path))
    except Exception:
        return None

    rows = []
    for q in qsos:
        row = {k.upper(): v for k, v in q.items()}
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def parse_adif_simple(path: Path) -> pd.DataFrame:
    text = path.read_text(errors="ignore")
    records = re.split(r"<eor>", text, flags=re.IGNORECASE)

    def get_field(rec: str, field: str) -> str | None:
        m = re.search(rf"<{re.escape(field)}:\d+>([^<]*)", rec, flags=re.IGNORECASE)
        return m.group(1).strip() if m else None

    rows = []
    for rec in records:
        call = get_field(rec, "CALL")
        if not call:
            continue

        row = {
            "CALL": call,
            "COUNTRY": get_field(rec, "COUNTRY"),
            "CONT": get_field(rec, "CONT"),
            "BAND": get_field(rec, "BAND"),
            "QSO_DATE": get_field(rec, "QSO_DATE"),
            "TIME_ON": get_field(rec, "TIME_ON"),
            "DXCC": get_field(rec, "DXCC"),
        }
        rows.append(row)

    return pd.DataFrame(rows)


def load_adif(path: Path) -> pd.DataFrame:
    df = parse_adif_with_adif_io(path)
    if df is None:
        df = parse_adif_simple(path)

    if df.empty:
        raise ValueError("No QSO records found in ADIF.")

    # Normalize columns
    df.columns = [c.upper() for c in df.columns]

    for col in ["CALL", "COUNTRY", "CONT", "BAND", "QSO_DATE", "TIME_ON", "DXCC"]:
        if col not in df.columns:
            df[col] = None

    # Repair missing country from callsign mapping
    def repaired_country(row: pd.Series) -> str | None:
        country = row.get("COUNTRY")
        call = row.get("CALL")
        if isinstance(country, str) and country.strip():
            return country.strip()
        if isinstance(call, str) and call.strip() in CALLSIGN_COUNTRY_FIXES:
            return CALLSIGN_COUNTRY_FIXES[call.strip()]
        return country

    df["COUNTRY"] = df.apply(repaired_country, axis=1)

    # Normalize text
    for col in ["CALL", "COUNTRY", "CONT", "BAND"]:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    return df


# ----------------------------
# Chart generation
# ----------------------------

def save_pie_chart(counter: Counter, title: str, output_path: Path) -> None:
    labels = list(counter.keys())
    sizes = list(counter.values())

    plt.figure(figsize=(7, 7))
    plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


# ----------------------------
# Map generation
# ----------------------------

def load_world():
    import geopandas as gpd

    url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
    world = gpd.read_file(url)

    if "NAME" in world.columns and "name" not in world.columns:
        world = world.rename(columns={"NAME": "name"})
    if "ADMIN" in world.columns and "name" not in world.columns:
        world = world.rename(columns={"ADMIN": "name"})

    return world

def build_worked_country_set(df: pd.DataFrame, world_names: set[str]) -> tuple[set[str], set[str]]:
    countries = sorted(set(c for c in df["COUNTRY"].dropna() if str(c).strip()))
    mapped_names: set[str] = set()
    unmapped: set[str] = set()

    for c in countries:
        mapped = COUNTRY_NAME_MAP.get(c, c)
        if mapped in world_names:
            mapped_names.add(mapped)
        else:
            unmapped.add(c)

    if EXCLUDE_LOWER_48 and "United States of America" in mapped_names:
        mapped_names.remove("United States of America")

    return mapped_names, unmapped


def build_adjacency_graph(worked: gpd.GeoDataFrame) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)

    rows = list(worked[["name", "geometry"]].itertuples(index=False, name=None))
    for i, (name_i, geom_i) in enumerate(rows):
        for j in range(i + 1, len(rows)):
            name_j, geom_j = rows[j]
            try:
                if geom_i.touches(geom_j):
                    adjacency[name_i].add(name_j)
                    adjacency[name_j].add(name_i)
            except Exception:
                continue

    return adjacency


def greedy_color(nodes: list[str], adjacency: dict[str, set[str]], palette: list[str]) -> dict[str, str]:
    color_map: dict[str, str] = {}

    # Sort by descending degree first for better coloring
    nodes_sorted = sorted(nodes, key=lambda n: len(adjacency.get(n, set())), reverse=True)

    for node in nodes_sorted:
        used = {color_map[n] for n in adjacency.get(node, set()) if n in color_map}
        for color in palette:
            if color not in used:
                color_map[node] = color
                break
        else:
            color_map[node] = palette[0]

    return color_map


def save_world_map(df: pd.DataFrame, output_path: Path) -> tuple[int, int, set[str]]:
    world = load_world()

    if "name" not in world.columns:
        raise ValueError("World dataset does not contain a 'name' column.")

    world_names = set(world["name"].dropna().astype(str))
    worked_names, unmapped = build_worked_country_set(df, world_names)

    world["worked"] = world["name"].isin(worked_names)

    worked = world[world["worked"]].copy()
    adjacency = build_adjacency_graph(worked)
    colors = greedy_color(worked["name"].tolist(), adjacency, PALETTE)

    world["plot_color"] = BASEMAP_COLOR
    for country_name, color in colors.items():
        world.loc[world["name"] == country_name, "plot_color"] = color

    qso_count = len(df)
    dxcc_count = len(set(c for c in df["COUNTRY"].dropna() if str(c).strip()))

    fig, ax = plt.subplots(figsize=(14, 7))
    world.plot(ax=ax, color=world["plot_color"], edgecolor=BASEMAP_EDGE, linewidth=0.5)

    ax.set_axis_off()
    fig.suptitle(TITLE, fontsize=20, y=0.97)
    ax.set_title(SUBTITLE_TEMPLATE.format(qsos=qso_count, dxcc=dxcc_count), fontsize=11, pad=10)

    if unmapped:
        note = (
            f"Note: {len(unmapped)} smaller DXCC entities were not shown individually in the base world dataset."
        )
        fig.text(0.5, 0.035, note, ha="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    return qso_count, dxcc_count, unmapped


# ----------------------------
# Main
# ----------------------------

def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: python contest_summary_map.py "your_log.adi"')
        return 2

    adif_path = Path(sys.argv[1])
    if not adif_path.exists():
        print(f"File not found: {adif_path}")
        return 2

    try:
        df = load_adif(adif_path)
    except Exception as e:
        print(f"Failed to read ADIF: {e}")
        return 1

    # Basic counts
    band_counts = Counter(c for c in df["BAND"].dropna() if str(c).strip())
    cont_counts = Counter(c for c in df["CONT"].dropna() if str(c).strip())

    stem = adif_path.stem
    band_pie = adif_path.with_name(f"{stem}_band_distribution.png")
    cont_pie = adif_path.with_name(f"{stem}_continent_distribution.png")
    world_map = adif_path.with_name(f"{stem}_worked_countries_map.png")

    try:
        save_pie_chart(band_counts, f"{TITLE} – Band Distribution", band_pie)
        save_pie_chart(cont_counts, f"{TITLE} – Continent Distribution", cont_pie)
        qso_count, dxcc_count, unmapped = save_world_map(df, world_map)
    except Exception as e:
        print(f"Failed to generate graphics: {e}")
        return 1

    print("Done.")
    print(f"QSOs: {qso_count}")
    print(f"DXCC entities: {dxcc_count}")
    print(f"Band pie: {band_pie}")
    print(f"Continent pie: {cont_pie}")
    print(f"World map: {world_map}")
    if unmapped:
        print("Unmapped entities:", ", ".join(sorted(unmapped)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())