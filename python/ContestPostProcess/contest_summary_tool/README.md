# Contest Summary Tool

A Python utility for generating **post-event statistics, charts, and maps** from amateur radio **ADIF logs**.

The tool was developed to summarize multi-operator club activity during contests and special events. It produces operator statistics, band/mode summaries, and visual maps showing worked states, provinces, and DX entities.

Typical uses include:

- Club meeting presentations
- Post-event reports
- Contest summaries
- Activity visualization

The tool works directly on **ADIF log files** and enriches missing geographic data using several techniques including grid inference and optional QRZ lookups.

---

# Features

## Log analysis

From an ADIF file the tool produces:

- Total QSO count
- Band distribution
- Continent distribution
- Q count by operator
- Operating time by operator (session-based)
- Mode distribution

---

## Geographic visualization

Maps generated from the log:

- **World map** of worked countries
- **US states + Canadian provinces + DX map**
- **North America view** emphasizing Worked-All-States style coverage

Example map coloring:

- **Blue** — US states worked
- **Green** — Canadian provinces worked
- **Gold** — DX entities worked

---

## Data enrichment

Missing geographic fields can be filled using several techniques.

### 1. Callsign reuse

If a callsign appears multiple times in the log with location data, later QSOs reuse that information.

### 2. Grid inference

If a Maidenhead grid square is present, the tool infers:

- US state
- Canadian province

### 3. QRZ lookup (optional)

Missing information can be retrieved from the **QRZ XML API**.

Returned data may include:

- state
- country
- grid square

Results are cached locally to avoid repeated queries.

---

# Charts

The tool produces several PNG charts suitable for presentations.

## Band distribution

Pie chart showing QSOs by band.

## Continent distribution

Pie chart showing QSOs by continent.

## Q count by operator

Pie chart showing the number of QSOs contributed by each operator.

## Operating time by operator

Pie chart showing approximate operating time based on session detection.

A new session begins when the gap between QSOs exceeds a configurable threshold.

Default: 30 minutes

Minimum session duration is automatically set to: session_gap / 2

This prevents isolated QSOs from appearing as zero-length sessions.

---

# Mode-aware operator charts

Operator charts can optionally show the **mode breakdown within each operator**.

Modes are grouped into four categories:

| Category | ADIF Modes |
|--------|--------|
| CW | CW |
| PH | SSB, USB, LSB, PHONE |
| DIG | FT8, FT4, RTTY, PSK, Olivia, etc |
| Other | anything else |

When enabled, charts are rendered as **nested donut charts**.

Outer ring: operator share

Inner ring: mode breakdown per operator

This allows the chart to show both **who operated** and **how they operated**.

---

# Maps

Three map styles are available.

## Countries map

World map highlighting worked countries.

## States + DX map

Shows:

- US states worked
- Canadian provinces worked
- DX countries

## North America states map

Focused view emphasizing:

- US states
- Canadian provinces

Also displays the number of non-NA DX entities worked.

---

# Installation

Create a Python environment and install dependencies.

Example using **conda**:

```bash
conda create -n contestmaps python=3.11
conda activate contestmaps
pip install pandas matplotlib geopandas adif_io requests

# Usage

Basic Usage

python run_contest_summary.py LOGFILE.adi

Example:

python run_contest_summary.py "W1AW_7_event_log.adi"

Optional arguments
Enable QRZ lookups
--qrz yes

Requires environment variables:

QRZ_USERNAME
QRZ_PASSWORD
Map type
--map countries
--map states_dx
--map na_states_dx

Default:

countries
Session gap

Define the gap (minutes) used to split operating sessions.

--session-gap 30

Minimum session duration automatically becomes:

session_gap / 2
Operator mode breakdown

Control whether operator charts include mode information.

Suggested values:

--operator-modes off
--operator-modes donut
--operator-modes both

Meaning:

Value	Behavior
off	simple operator pie charts
donut	nested donut charts with mode breakdown
both	generate both versions
Output

The tool generates files in the output directory.

Typical output:

summary.txt
band_distribution.png
continent_distribution.png
operator_qcount.png
operator_time.png
countries_map.png
states_dx_map.png
na_states_dx_map.png

If donut charts are enabled:

operator_qcount_donut.png
operator_time_donut.png
QRZ caching

QRZ lookups are cached locally:

qrz_cache.json

This dramatically speeds up subsequent runs.

Cache entries automatically expire depending on the callsign type.

Typical TTL values:

Callsign type	TTL
Portable callsigns	~3 days
Normal callsigns	~180 days
Failed lookups	~7 days
Example workflow

Typical usage after a contest:

python run_contest_summary.py event_log.adi --qrz yes --map na_states_dx

Produces:

enriched summary statistics

charts for presentation

maps for reports

Future improvements

Ideas under consideration:

Cabrillo log input

DXCC entity maps

time-of-day activity charts

band × operator heatmaps

HTML summary report

License

Open source. Use and modify freely.