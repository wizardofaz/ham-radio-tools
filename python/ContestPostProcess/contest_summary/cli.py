import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate contest summary graphics from ADIF logs."
    )
    parser.add_argument(
        "adif",
        help="Path to ADIF log file",
    )
    parser.add_argument(
        "--title",
        help="Title for charts and maps",
    )
    parser.add_argument(
        "--map",
        default="countries",
        choices=["all", "countries", "states_dx", "na_states_dx"],
        help="Map mode",
    )
    parser.add_argument(
        "--qrz",
        default="no",
        choices=["yes", "no"],
        help="Allow QRZ lookup",
    )
    parser.add_argument(
        "--outdir",
        help="Output directory (default is same directory as first ADIF input file) ",
    )
    parser.add_argument(
        "--include-lower48",
        default="no",
        choices=["yes", "no"],
        help="Include continental US in country map",
    )
    parser.add_argument(
        "--summary",
        default="yes",
        choices=["yes", "no"],
        help="Write text summary file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing generated output files",
    )

    parser.add_argument(
        "--session-gap-minutes",
        type=int,
        help="Gap threshold (minutes) used to split operating sessions"
    )

    parser.add_argument(
        "--config",
        help="Path to configuration JSON file (default: ./config.json)"
    )

    parser.add_argument(
        "--qrz-cache-path",
        help="Path to cache file for QRZ.com lookups, created if doesn't exist (default: {specified --outdir}/qrz_cache.json)"
    )

    args = parser.parse_args()

    args.qrz = args.qrz == "yes"
    args.summary = args.summary == "yes"
    args.include_lower48 = args.include_lower48 == "yes"

    if not args.outdir:
        adif_path = Path(args.adif)
        args.outdir = str(adif_path.parent)

    if not args.qrz_cache_path:
        args.qrz_cache_path = str(Path(args.outdir) / 'qrz_cache.json')
    

    return args