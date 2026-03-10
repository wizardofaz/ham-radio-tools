# Contest Summary Tool

A Python utility for generating summary graphics and statistics from ADIF contest logs.

The script produces:

- Band distribution pie chart
- Continent distribution pie chart
- Map of contacts (various styles)
- Optional text summary for easy sharing

It works well for both **DX-heavy contests** and **domestic-focused events** such as WAS activations.

---

---

# Quick Start

Run the tool in just a few steps.

## 1. Clone or download the project

```
git clone <repo-url>
cd contest-summary
```

or simply download the files and change into that directory.

---

## 2. Create a Python virtual environment

```
python -m venv venv
```

Activate it.

Windows:

```
venv\Scripts\activate
```

Linux / macOS:

```
source venv/bin/activate
```

---

## 3. Install required packages

```
pip install -r requirements.txt
```

---

## 4. Run the tool

Example:

```
python contest_summary.py "K7RST 2026 ARRL DX PH.adi"
```

This will generate:

- band distribution chart
- continent distribution chart
- contact map
- summary text file

All outputs will be written to the same directory as the ADIF file.

---

## Example with options

```
python contest_summary.py "W1AW_7_event.adi" \
    --title "WAS50-AZ Event Summary" \
    --map states_dx \
    --qrz yes \
    --outdir results
```

This will produce the same charts and maps, but:

- with a custom title
- using the state/province map mode
- performing QRZ lookups for missing information
- writing output files into the `results` directory.

---

# Usage

```
python contest_summary.py LOGFILE.adi [options]
```

Example:

```
python contest_summary.py log.adi \
    --title "WAS50-AZ Event Summary" \
    --map states_dx \
    --qrz yes \
    --outdir results
```

---

# Required Argument

### `LOGFILE.adi`

Path to the ADIF file to process.

Example:

```
python contest_summary.py "K7RST 2026 ARRL DX PH.adi"
```

---

# Optional Arguments

## `--title`

Sets the title used on charts and maps.

Default: derived from the ADIF filename.

Example:

```
--title "ARRL DX SSB 2026 — K7RST"
```

---

## `--map`

Selects the map style.

Available modes:

| Mode | Description |
|-----|-------------|
| `countries` | World map highlighting worked countries |
| `states_dx` | World map showing US states, Canadian provinces, and non-NA DX countries |
| `na_states_dx` | North America–focused map highlighting states/provinces |

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

## `--qrz`

Allows QRZ.com lookups to fill missing information.

Lookup occurs **only if needed**, when the log lacks state/province/country/grid data.

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

## `--outdir`

Directory where generated files will be written.

Default: same directory as the input ADIF file.

Example:

```
--outdir results
```

---

## `--include-lower48`

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

## `--summary`

Controls generation of a plain-text summary file.

Values:

```
yes
no
```

Default:

```
yes
```

The summary file is useful for posting results to email or web pages.

---

# Map Modes

## `countries`

World map showing:

- Worked countries
- Non-worked countries shaded lightly

Best suited for **DX contests**.

---

## `states_dx`

Full world map showing:

- US states worked
- Canadian provinces worked
- Non-North-American DX countries

Best suited for events with both **domestic and DX contacts**, such as:

- WAS activations
- special event stations

---

## `na_states_dx`

North America-focused map showing:

- US states worked
- Canadian provinces worked

DX outside North America may be summarized separately.

Best suited for **domestic-focused events**.

---

# Data Enrichment Pipeline

To improve map accuracy, the script attempts to fill missing location information.

Steps are applied in the following order:

### 1. Use values already present in the ADIF log

Fields used directly if available:

- `STATE`
- `VE_PROV`
- `COUNTRY`
- `CONT`

---

### 2. Reuse information from other QSOs with the same callsign

If a callsign appears multiple times and one entry contains state/province information, it will be reused for the others.

Example:

```
K1ABC  STATE=MA
K1ABC  STATE missing
```

The second entry will inherit `MA`.

---

### 3. Infer from grid square

When available, grid squares can often determine state or province.

Example:

```
FN42 → Massachusetts
CN87 → Washington
```

This avoids unnecessary external lookups.

---

### 4. Optional QRZ lookup

If enabled, QRZ lookups may supply missing fields such as:

- state
- country
- grid

QRZ lookups occur **only when earlier steps fail**.

---

# Output Files

Generated files are written to the output directory.

Example outputs:

```
log_band_distribution.png
log_continent_distribution.png
log_states_dx_map.png
log_summary.txt
```

The map filename suffix reflects the selected map mode.

---

# Example Commands

## DX Contest

```
python contest_summary.py "K7RST 2026 ARRL DX PH.adi" \
    --title "K7RST ARRL DX SSB 2026" \
    --map countries
```

---

## WAS Event

```
python contest_summary.py "W1AW_7_event.adi" \
    --title "WAS50-AZ Event Summary" \
    --map states_dx
```

---

## WAS Event with QRZ lookups and separate output folder

```
python contest_summary.py "W1AW_7_event.adi" \
    --title "WAS50-AZ Event Summary" \
    --map states_dx \
    --qrz yes \
    --outdir results
```

---

# Requirements

Typical Python dependencies:

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

or via a conda environment if preferred.

---

# Future Enhancements

Possible future additions include:

- QSO rate graphs
- operator contribution summaries
- band vs continent matrices
- DX spider maps
- automated HTML reports

---

# License

Open source. Modify and share as needed within the amateur radio community.