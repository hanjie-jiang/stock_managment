"""Local per-install settings (currently just display language).

Stored as settings.json next to this file -- gitignored, following the exact
pattern of watchlist_store.py, since it's this install's own preference
(which language this PC's viewer reads), not code.
"""

import json
import os

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

_DEFAULT_SETTINGS = {"language": "en"}


def load_settings():
    if os.path.exists(_PATH):
        with open(_PATH, encoding="utf-8") as f:
            return {**_DEFAULT_SETTINGS, **json.load(f)}
    save_settings(_DEFAULT_SETTINGS)
    return dict(_DEFAULT_SETTINGS)


def save_settings(settings):
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
