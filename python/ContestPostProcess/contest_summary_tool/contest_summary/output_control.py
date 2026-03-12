from pathlib import Path


def should_write_output(outfile, overwrite=False):
    """
    Decide whether a generated output file should be written.

    Returns True if the caller should proceed with writing the file.
    Returns False if the file already exists and overwrite is not enabled.
    """
    outfile = Path(outfile)

    if outfile.exists():
        if not overwrite:
            print(f"WARNING: Output file exists, skipping: {outfile}")
            return False
        print(f"Overwriting existing file: {outfile}")

    return True