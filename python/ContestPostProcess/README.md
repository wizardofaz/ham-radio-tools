# Contest Summary Tool

A Python utility for generating summary graphics and statistics from ADIF contest logs.

The tool parses ADIF logs, enriches missing geographic data when possible, and produces charts and maps suitable for post-event reports or activity summaries.

It works well for both:

- DX-heavy contests
- domestic-focused events such as WAS activations or special event stations


---

# Overview

`contest_summary` analyzes ADIF logs and produces visual summaries of operating activity.

Typical uses include:

- post-event reports
- club activity summaries
- operator participation analysis
- quick graphics for websites or social media

The tool is designed to handle **multi-operator logs**, including logs where multiple operators are active simultaneously.


---

# Key Features

## Log Processing

- Reads standard **ADIF** logs
- Handles **interleaved QSOs from multiple operators**
- Automatically separates operators before analysis

## Data Enrichment

Optional enrichment improves chart and map accuracy when ADIF fields are incomplete.

Steps include:

- **Callsign reuse** from other QSOs in the log
- **Grid square inference**
- **Optional QRZ.com lookup**
- A second inference pass after QRZ enrichment

## Session Analysis

Operating sessions are inferred from QSO timestamps.

Sessions are split when:

- the time gap between QSOs exceeds a threshold, or
- the operator changes mode

The session gap threshold defaults to **30 minutes**.

Sessions shorter than half the threshold are credited with a minimum duration equal to **half the threshold**.

This avoids zero-length sessions from isolated QSOs.


---

# Generated Outputs

## Charts

| File | Description |
|-----|-------------|
| `band_distribution.png` | QSO distribution by band |
| `mode_distribution.png` | QSO distribution by mode |
| `continent_distribution.png` | QSO distribution by continent |
| `operator_qso_distribution.png` | QSOs by operator (outer ring shows mode) |
| `operator_time_distribution.png` | Operating time by operator (outer ring shows mode) |

### Operator Donut Charts

Two nested donut charts are produced.

**QSOs by Operator**

- inner ring: operator share of QSOs
- outer ring: mode distribution for each operator

**Operating Time by Operator**

- inner ring: operator share of operating time
- outer ring: mode distribution for each operator

Mode colors are consistent across charts:

| Mode | Color |
|-----|------|
| CW | blue |
| PH | orange |
| DIG | green |
| Other | gray |

These paired charts highlight differences between:

- operators who spend the most time on the air
- operators who achieve the highest QSO rates


---

## Maps

| File | Description |
|-----|-------------|
| `states_dx_map.png` | Map of worked states and DX locations |

Maps rely on grid and callsign information derived from the enrichment process.


---

# Configuration

Optional configuration can be provided via `config.json` in the working directory.

Example:

```json
{
  "session_gap_minutes": 30,
  "mode_categories": {
    "CW": ["CW"],
    "PH": ["SSB", "USB", "LSB", "FM", "AM"],
    "DIG": ["FT8", "FT4", "MFSK", "RTTY"]
  }
}
```

Configuration precedence:

```
CLI options
    override
config.json
    override
built-in defaults
```


---

# Quick Start

## 1. Clone the repository

```
git clone https://github.com/wizardofaz/ham-radio-tools.git
cd ham-radio-tools/python/ContestPostProcess
```

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

## 3. Install dependencies

The map feature uses GeoPandas which depends on GDAL.

On Linux you may need to install GDAL before installing the Python requirements.

Example (Debian/Ubuntu):

    sudo apt install gdal-bin libgdal-dev

Then install Python requirements:

    pip install -r requirements.txt

```
pip install -r requirements.txt
```

## 4. Run the tool

Example:

```
python run_contest_summary.py "K7RST 2026 ARRL DX PH.adi"
```

An alternative invocation using the package entry point is also supported:

```
python -m contest_summary "K7RST 2026 ARRL DX PH.adi"
```

Outputs are written to the same directory as the ADIF file unless otherwise specified.


---

# Usage

```
python run_contest_summary.py LOGFILE.adi [options]
```

Example:

```
python run_contest_summary.py log.adi \
  --title "WAS50-AZ Event Summary" \
  --map states_dx \
  --qrz yes \
  --outdir results
```


---

# Required Argument

## LOGFILE.adi

Path to the ADIF file to process.

Example:

```
python run_contest_summary.py "K7RST 2026 ARRL DX PH.adi"
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

| Mode | Description |
|-----|-------------|
| `countries` | World map highlighting worked countries |
| `states_dx` | World map showing US states, Canadian provinces, and DX countries |
| `na_states_dx` | North America–focused map highlighting states/provinces |

Default:

```
countries
```

---

## --qrz

Allows QRZ.com lookups to fill missing location data.

Values:

```
yes
no
```

Default:

```
no
```

QRZ credentials must be provided via environment variables:

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

Applies to:

- chart PNG files
- map PNG files
- summary text files

Default behavior without `--overwrite`:

- existing generated files are left in place
- a warning is printed for each existing file
- missing outputs are still generated

`qrz_cache.json` is not affected by `--overwrite`.

Example:

```
python run_contest_summary.py log.adi --overwrite
```


---

# Data Enrichment Pipeline

To improve map accuracy, the tool fills missing location information in stages.

## 1. Use values already present in the ADIF log

Fields used directly include:

- STATE
- VE_PROV
- COUNTRY
- CONT
- GRIDSQUARE

## 2. Reuse information from other QSOs with the same callsign

If another QSO for the same callsign contains location data, it may be reused.

## 3. Infer from grid square

Grid squares can often determine state or province.

## 4. Optional QRZ lookup

If enabled, QRZ lookups may supply:

- state
- country
- grid square

Lookups are attempted only when earlier steps fail.

A local cache (`qrz_cache.json`) prevents repeated lookups.


---

# Smoke Test

A small test dataset is included.

```
testdata/
  input/
    sample_log.adi
    qrz_cache.json
  output/
```

Run the smoke test from the `ContestPostProcess` directory:

```
test.cmd
```

The test verifies that:

- log parsing works
- enrichment runs
- charts and maps generate correctly

Generated files are written to `testdata/output/`, which is ignored by git.

The included `qrz_cache.json` is pre-seeded so that:

- most lookups are satisfied locally
- a few calls require live QRZ queries when `--qrz yes` is used


---

# Requirements

Typical dependencies include:

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

# Future Enhancements

Possible future additions include:

- support for multiple ADIF input files
- operator QSO rate analysis
- additional charts and summary metrics
- configurable chart selection
- automated HTML report generation


---

# License

Open source. Modify and share as needed within the amateur radio community.