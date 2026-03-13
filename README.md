# Ham Radio Tools

This repository contains small utilities for amateur radio logging, ADIF processing, and contest/event post-processing.

Most tools are simple standalone scripts intended to be easy to run, modify, and reuse in other ham-radio workflows.

The emphasis is on **practical tools that solve real operating problems** rather than large frameworks.

---

# Quick Start

Clone the repository:

```bash
git clone https://github.com/wizardofaz/ham-radio-tools.git
cd ham-radio-tools
```

Navigate to the tool you want to run:

```bash
cd python/ADIF_tools
```

Run the script with Python:

```bash
python split_adif_by_operator.py input_log.adif
```

Most tools accept command-line arguments and will print usage help when run with:

```bash
-h
```

---

# Tools

## Python Tools

### ADIF Tools

Utilities for working with ADIF log files.

#### `split_adif_by_operator.py`

Splits a single ADIF log into separate ADIF files based on the `OPERATOR` field.

Useful when:

- multiple operators contributed to a combined log
- individual logs must be submitted separately
- operator activity needs to be analyzed independently

Typical use case:

```bash
python split_adif_by_operator.py combined_log.adif
```

The script produces one ADIF file per operator.

---

### Contest Post-Processing

Utilities for analyzing contest or special-event logs after operating is complete.

Location:

```
python/ContestPostProcess
```

The primary tool is **contest_summary**, which generates charts, maps, and statistics from an ADIF log.

Typical outputs include:

- band distribution charts
- mode distribution charts
- continent distribution charts
- operator participation charts
- estimated operator airtime (session analysis)
- geographic contact maps

These outputs are intended for:

- contest summaries
- club reports
- special event documentation
- operator participation analysis

Example usage:

```bash
python run_contest_summary.py event_log.adi
```

or

```bash
python -m contest_summary event_log.adi
```

See the full documentation here:

```
python/ContestPostProcess/README.md
```

---

# Repository Structure

```
ham-radio-tools
├─ python/
│  ├─ ADIF_tools/
│  │   └─ utilities for manipulating ADIF logs
│  │
│  └─ ContestPostProcess/
│      └─ contest and event analysis tools
```

Additional tools may be added over time.

---

# Goals

This repository focuses on:

- practical ham-radio utilities
- tools for ADIF log processing
- scripts that are easy to understand and modify
- sharing useful tools with the amateur radio community

Many tools begin as personal utilities and evolve into reusable scripts.

---

# License

Open source. Feel free to use, modify, and share these tools within the amateur radio community.