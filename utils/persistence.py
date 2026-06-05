"""
utils/persistence.py
--------------------
Lightweight JSON-file persistence for expense, asset, and liability data.

Why JSON files?
  - Zero extra dependencies (no database server required)
  - Works identically on every OS
  - Data survives Flask restarts and hot-reloads
  - Trivially replaceable with SQLite/PostgreSQL later

All public helpers are thread-safe via a per-store threading.Lock.
"""

import json
import os
import threading
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(_DATA_DIR, exist_ok=True)

_STORE_PATHS = {
    "expenses": os.path.join(_DATA_DIR, "expenses.json"),
    "assets": os.path.join(_DATA_DIR, "assets.json"),
    "liabilities": os.path.join(_DATA_DIR, "liabilities.json"),
}

_locks: Dict[str, threading.Lock] = {key: threading.Lock() for key in _STORE_PATHS}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read(store: str) -> List[Dict[str, Any]]:
    """Return the list stored in *store*, or [] if the file doesn't exist yet."""
    path = _STORE_PATHS[store]
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write(store: str, data: List[Dict[str, Any]]) -> None:
    """Persist *data* to the JSON file for *store*."""
    path = _STORE_PATHS[store]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load(store: str) -> List[Dict[str, Any]]:
    """Thread-safe read of *store*."""
    with _locks[store]:
        return _read(store)


def append_item(store: str, item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Append *item* to *store* and return the updated list."""
    with _locks[store]:
        data = _read(store)
        # Assign a stable UUID-style id so deletions never corrupt indices
        item["id"] = max((d.get("id", -1) for d in data), default=-1) + 1
        data.append(item)
        _write(store, data)
        return data


def delete_item(store: str, item_id: int) -> List[Dict[str, Any]]:
    """Remove the item with *item_id* from *store* and return the updated list.

    Uses id-based lookup instead of list index so that deletions are safe
    even after previous removals.
    """
    with _locks[store]:
        data = _read(store)
        new_data = [d for d in data if d.get("id") != item_id]
        if len(new_data) == len(data):
            raise KeyError(f"No item with id={item_id} found in store '{store}'")
        _write(store, new_data)
        return new_data


def clear(store: str) -> None:
    """Erase all records in *store* (useful for testing)."""
    with _locks[store]:
        _write(store, [])
