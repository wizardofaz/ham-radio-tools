# Contest Summary Tool

A Python utility for generating summary graphics and statistics from ADIF contest logs.

Current outputs include:

- Band distribution pie chart
- Continent distribution pie chart
- Contact map (various styles)
- Plain-text summary report

The tool also performs data enrichment to improve map and summary quality when ADIF fields are incomplete.

---

# Quick Start

## 1. Clone the repository

```
git clone https://github.com/wizardofaz/ham-radio-tools.git
cd ham-radio-tools/python/ContestPostProcess
```

## 2. Create and activate a virtual environment

Windows:

```
python -m venv venv
venv\Scripts\activate
```

Linux / macOS:

```
python -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

```
pip install -r requirements.txt
```

---

# Running the Tool

Basic example:

```
python contest_summary.py "K7RST 2026 ARRL DX PH.adi"
```

By default, outputs are written to the same directory as the input ADIF file.

Example with options:

```
python contest_summary.py "W1AW_7_event.adi" \
  --title "WAS50-AZ Event Summary" \
  --map states_dx \
  --qrz yes \
  --outdir results
```

Example forcing chart regeneration:

```
python contest_summary.py "W1AW_7_event.adi" \
  --title "WAS50-AZ Event Summary" \
  --map states_dx \
  --qrz yes \
  --outdir results \
  --overwrite
```

---

# Usage

```
python contest_summary.py LOGFILE.adi [options]
```

---

# Required Argument

## LOGFILE.adi

Path to the ADIF file to process.

Example:

```
python contest_summary.py "K7RST 2026 ARRL DX PH.adi"
```

---

# Optional Arguments

## --title

Sets the title used on charts and maps.

Default: derived from the ADIF filename.

Example:

```
--title "ARRL DX SSB 2026 — K7RST"
```

---

## --map

Selects the map style.

Available modes:

| Mode | Description |
|-----|-------------|
| countries | World map highlighting worked countries |
| states_dx | World map showing US states, Canadian provinces, and non-NA DX countries |
| na_states_dx | North America–focused map highlighting states and provinces |

Default:

```
countries
```

Examples:

```
--map countries
--map states_dx
--map na_states_dx
```

---

## --qrz

Allows QRZ.com lookups to fill missing information.

Lookup occurs only when needed, after local enrichment steps do not provide enough data.

Values:

```
yes
no
```

Default:

```
no
```

Example:

```
--qrz yes
```

QRZ credentials are expected via environment variables:

```
QRZ_USERNAME
QRZ_PASSWORD
```

---

## --outdir

Directory where generated files will be written.

Default: same directory as the input ADIF file.

Example:

```
--outdir results
```

---

## --include-lower48

Controls whether the continental US is highlighted in `countries` map mode.

Values:

```
yes
no
```

Default:

```
no
```

---

## --summary

Controls generation of the plain-text summary file.

Values:

```
yes
no
```

Default:

```
yes
```

---

## --overwrite

Overwrite previously generated output files.

This applies to:

- chart PNG files
- map PNG files
- `summary.txt`

Default behavior without `--overwrite`:

- existing generated output files are left in place
- a warning is printed for each existing output file
- files that do not yet exist are still generated

This does **not** apply to `qrz_cache.json`, which is a lookup cache used to speed future runs.

Example:

```
python contest_summary.py "W1AW_7_event.adi" --outdir results --overwrite
```

# Data Enrichment Pipeline

To improve output quality, the tool attempts to fill missing location-related information in stages.

## 1. Use values already present in the ADIF log

Fields used directly when available include:

- STATE
- VE_PROV
- COUNTRY
- CONT
- GRIDSQUARE

---

## 2. Reuse values from other QSOs with the same callsign

If the same callsign appears elsewhere in the log with better location data, that information may be reused.

---

## 3. Infer from grid square

When a grid square is present, the tool may infer state or province.

This helps avoid unnecessary external lookups.

---

## 4. Optional QRZ lookup

If enabled, QRZ lookups may supply missing values such as:

- state
- province
- country
- grid square

QRZ lookups are attempted only after the earlier enrichment steps.

A cache file is written in the output directory to reduce repeated lookups on later runs.

---

# Output Files

Generated files are written to the output directory.

Typical outputs include:

```
band_distribution.png
continent_distribution.png
summary.txt
qrz_cache.json
```

The map filename depends on the selected map mode and current map rendering logic.

---

# Map Modes

## countries

World map showing worked countries.

Best suited for DX-heavy contests.

---

## states_dx

Full world map showing:

- US states worked
- Canadian provinces worked
- DX countries outside North America

Best suited for mixed domestic/DX events such as special-event stations and WAS-style activity.

---

## na_states_dx

North America-focused map showing:

- US states worked
- Canadian provinces worked

Useful for domestic-focused events.

---

# Example Commands

## DX Contest

```
python contest_summary.py "K7RST 2026 ARRL DX PH.adi" \
  --title "K7RST ARRL DX SSB 2026" \
  --map countries
```

## WAS-Style Event

```
python contest_summary.py "W1AW_7_event.adi" \
  --title "WAS50-AZ Event Summary" \
  --map states_dx
```

## WAS-Style Event with QRZ lookups and overwrite

```
python contest_summary.py "W1AW_7_event.adi" \
  --title "WAS50-AZ Event Summary" \
  --map states_dx \
  --qrz yes \
  --outdir results \
  --overwrite
```

---

# Requirements

Typical Python dependencies include:

- matplotlib
- pandas
- geopandas
- geodatasets
- shapely
- pyproj
- fiona
- pyogrio
- adif_io

Install with:

```
pip install -r requirements.txt
```

---

# Notes

- Charts are currently generated as PNG files.
- Existing generated output files are skipped unless `--overwrite` is given.
- `qrz_cache.json` is cache data and is not governed by `--overwrite`.
- Map counts and chart set may continue to evolve as the project develops.

---

# License

Open source. Modify and share as needed within the amateur radio community.---

# Project Structure

The contest summary tool is implemented as a small Python package within the repository.

```
python/ContestPostProcess/
│
├─ contest_summary.py
│     Entry-point script used to run the tool.
│
├─ requirements.txt
│     Python dependencies required for maps, charts, and ADIF parsing.
│
├─ README.md
│     Documentation for this tool.
│
└─ contest_summary_tool/
      Python package containing the implementation.

      └─ contest_summary/
           │
           ├─ cli.py
           │     Command-line argument parsing.
           │
           ├─ main.py
           │     Main workflow coordinating parsing, enrichment,
           │     chart generation, maps, and summaries.
           │
           ├─ adif_utils.py
           │     ADIF parsing and initial data loading.
           │
           ├─ enrich.py
           │     Data enrichment pipeline including:
           │       • callsign reuse
           │       • grid inference
           │       • optional QRZ lookup
           │
           ├─ qrz_lookup.py
           │     QRZ API interaction and local cache handling.
           │
           ├─ charts.py
           │     Chart generation using matplotlib.
           │
           ├─ maps.py
           │     Geographic map rendering using GeoPandas.
           │
           └─ summary.py
                 Plain-text summary report generation.
```

This modular layout keeps responsibilities separated and makes it easier to extend the tool with additional charts, maps, or enrichment steps.