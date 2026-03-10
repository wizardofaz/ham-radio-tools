# Ham Radio Tools

This repository contains small utilities for amateur radio logging, ADIF processing, and contest/event post-processing.

Most tools are simple standalone scripts intended to be easy to run, modify, and reuse in other ham-radio workflows.

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

Most tools accept command-line arguments and print help if run with `-h`.

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

Utilities for analyzing or summarizing contest and special-event logs.

#### `contest_summary.py`

Generates summary statistics from an ADIF log file for contest or event analysis.

Typical outputs may include:

- QSO counts
- band/mode breakdowns
- geographic distribution of contacts
- statistics useful for post-event reports

Example usage:

```bash
python contest_summary.py event_log.adif
```

---

# Repository Structure

```
ham-radio-tools
├─ python/
│  ├─ ADIF_tools/
│  └─ ContestPostProcess/
```

Additional tools (including web-based utilities) may be added over time.

---

# Goals

This repository focuses on:

- practical ham-radio utilities
- tools for ADIF log processing
- scripts that are easy to understand and adapt
- sharing useful post-processing tools with the amateur radio community
