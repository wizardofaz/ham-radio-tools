from functools import lru_cache
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box


# You can replace this with a local file path later if you prefer.
ADMIN1_SOURCE = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"

TARGET_COUNTRIES = {
    "United States of America": "US",
    "Canada": "CA",
    "Mexico": "MX",
}

US_STATE_ABBREV = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME",
    "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

CANADA_PROV_ABBREV = {
    "Alberta": "AB", "British Columbia": "BC", "Manitoba": "MB",
    "New Brunswick": "NB", "Newfoundland and Labrador": "NL",
    "Northwest Territories": "NT", "Nova Scotia": "NS", "Nunavut": "NU",
    "Ontario": "ON", "Prince Edward Island": "PE", "Quebec": "QC",
    "Saskatchewan": "SK", "Yukon": "YT",
}

MEXICO_STATE_ABBREV = {
    "Aguascalientes": "AGU", "Baja California": "BCN", "Baja California Sur": "BCS",
    "Campeche": "CAM", "Chiapas": "CHP", "Chihuahua": "CHH", "Coahuila": "COA",
    "Colima": "COL", "Durango": "DUR", "Guanajuato": "GUA", "Guerrero": "GRO",
    "Hidalgo": "HID", "Jalisco": "JAL", "México": "MEX", "Mexico City": "CMX",
    "Michoacán": "MIC", "Morelos": "MOR", "Nayarit": "NAY", "Nuevo León": "NLE",
    "Oaxaca": "OAX", "Puebla": "PUE", "Querétaro": "QUE", "Quintana Roo": "ROO",
    "San Luis Potosí": "SLP", "Sinaloa": "SIN", "Sonora": "SON", "Tabasco": "TAB",
    "Tamaulipas": "TAM", "Tlaxcala": "TLA", "Veracruz": "VER", "Yucatán": "YUC",
    "Zacatecas": "ZAC",
}


def maidenhead_box(grid: str):
    """
    Return a shapely box for a 4- or 6-character Maidenhead grid square.
    """
    if not grid:
        return None

    g = grid.strip().upper()
    if len(g) < 4:
        return None
    if len(g) not in (4, 6):
        g = g[:6] if len(g) >= 6 else g[:4]

    try:
        lon = (ord(g[0]) - ord("A")) * 20 - 180
        lat = (ord(g[1]) - ord("A")) * 10 - 90

        lon += int(g[2]) * 2
        lat += int(g[3]) * 1

        if len(g) == 4:
            width = 2.0
            height = 1.0
        else:
            lon += (ord(g[4]) - ord("A")) * (1.0 / 12.0)
            lat += (ord(g[5]) - ord("A")) * (1.0 / 24.0)
            width = 1.0 / 12.0
            height = 1.0 / 24.0

        return box(lon, lat, lon + width, lat + height)
    except Exception:
        return None


def _pick_col(gdf, candidates):
    for col in candidates:
        if col in gdf.columns:
            return col
    return None


def _normalize_country_name(name: str):
    if not name:
        return None
    name = str(name).strip()
    aliases = {
        "United States": "United States of America",
        "United States of America": "United States of America",
        "USA": "United States of America",
        "Canada": "Canada",
        "Mexico": "Mexico",
    }
    return aliases.get(name, name)


def _admin1_abbrev(country_name: str, admin1_name: str, postal: str | None):
    if postal and str(postal).strip():
        return str(postal).strip().upper()

    if country_name == "United States of America":
        return US_STATE_ABBREV.get(admin1_name)
    if country_name == "Canada":
        return CANADA_PROV_ABBREV.get(admin1_name)
    if country_name == "Mexico":
        return MEXICO_STATE_ABBREV.get(admin1_name)

    return None


@lru_cache(maxsize=1)
def load_admin1():
    gdf = gpd.read_file(ADMIN1_SOURCE)
    gdf = gdf.to_crs("EPSG:4326")

    country_col = _pick_col(gdf, ["admin", "adm0_name", "geonunit", "sr_adm0_a3"])
    name_col = _pick_col(gdf, ["name", "name_en", "gn_name", "woe_name"])
    postal_col = _pick_col(gdf, ["postal", "postal_code", "iso_3166_2"])

    if not country_col or not name_col:
        raise RuntimeError(
            f"Could not identify expected admin-1 columns. Found: {list(gdf.columns)}"
        )

    gdf = gdf.rename(columns={
        country_col: "country_name",
        name_col: "admin1_name",
    }).copy()

    if postal_col:
        gdf = gdf.rename(columns={postal_col: "postal"})
    else:
        gdf["postal"] = None

    gdf["country_name"] = gdf["country_name"].apply(_normalize_country_name)
    gdf = gdf[gdf["country_name"].isin(TARGET_COUNTRIES.keys())].copy()

    # Keep only polygonal rows with valid geometry
    gdf = gdf[gdf.geometry.notnull()].copy()

    return gdf[["country_name", "admin1_name", "postal", "geometry"]]


def infer_admin1_from_grid(grid: str):
    """
    Return a dict like:
        {
            "country_name": "United States of America",
            "country_code": "US",
            "admin1_name": "Arizona",
            "admin1_abbrev": "AZ",
            "grid_precision": 6,
        }
    or None if ambiguous / unresolved.
    """
    geom = maidenhead_box(grid)
    if geom is None:
        return None

    admin1 = load_admin1()

    # Intersections with relevant target polygons only.
    hits = admin1[admin1.geometry.intersects(geom)].copy()

    # Ignore ocean/empty space automatically: only real admin-1 polygons count.
    if len(hits) != 1:
        return None

    row = hits.iloc[0]
    country_name = row["country_name"]
    admin1_name = row["admin1_name"]
    postal = row.get("postal")

    return {
        "country_name": country_name,
        "country_code": TARGET_COUNTRIES[country_name],
        "admin1_name": admin1_name,
        "admin1_abbrev": _admin1_abbrev(country_name, admin1_name, postal),
        "grid_precision": 6 if len(grid.strip()) >= 6 else 4,
    }


def infer_us_state_from_grid(grid: str):
    result = infer_admin1_from_grid(grid)
    if not result:
        return None
    if result["country_code"] != "US":
        return None
    return result["admin1_abbrev"]


def infer_canada_prov_from_grid(grid: str):
    result = infer_admin1_from_grid(grid)
    if not result:
        return None
    if result["country_code"] != "CA":
        return None
    return result["admin1_abbrev"]


def infer_mexico_state_from_grid(grid: str):
    result = infer_admin1_from_grid(grid)
    if not result:
        return None
    if result["country_code"] != "MX":
        return None
    return result["admin1_abbrev"]
