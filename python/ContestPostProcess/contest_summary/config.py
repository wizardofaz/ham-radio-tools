# Not Intended for user editing. 
# config.py provides some base defaults but the correct place to update defaults is config.json
# or one-time config changes as CLI options. 
#
import json
from pathlib import Path

DEFAULT_CONFIG = {
    "session_gap_minutes": 30,
    "mode_categories": {
        "CW": ["CW"],
        "PH": ["SSB", "USB", "LSB", "FM", "AM"],
        "DIG": ["FT8", "FT4", "MFSK", "RTTY", "PSK31", "JT65", "JT9"]
    }
}


def load_config(config_path=None):
    """
    Load configuration from config.json if present.
    Returns a dict merged with DEFAULT_CONFIG.
    """
    config = DEFAULT_CONFIG.copy()

    if config_path:
        path = Path(config_path)
    else:
        path = Path("config.json")

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            user_config = json.load(f)

        # merge simple keys
        for k, v in user_config.items():
            config[k] = v

    return config


def apply_cli_overrides(config, args):
    """
    Override config values with CLI arguments if provided.
    """
    if getattr(args, "session_gap_minutes", None) is not None:
        config["session_gap_minutes"] = args.session_gap_minutes

    return config