import argparse


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
        choices=["countries", "states_dx", "na_states_dx"],
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
        help="Output directory",
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

    args = parser.parse_args()
    args.qrz = args.qrz == "yes"
    args.summary = args.summary == "yes"
    args.include_lower48 = args.include_lower48 == "yes"
    return args