"""Common types and constants for the file integrity monitor."""

from __future__ import annotations

from typing import Any, Dict

Inventory = Dict[str, Dict[str, Any]]
DEFAULT_INTERVAL_MINUTES = 60
