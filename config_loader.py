"""Chargeur de configuration centralisé."""
import json
from pathlib import Path

_IOS_CONFIG = Path(__file__).parent / "config" / "ios_config.json"


def get_ios_port() -> int:
    try:
        with open(_IOS_CONFIG) as f:
            return json.load(f).get("server_port", 7777)
    except Exception:
        return 7777
