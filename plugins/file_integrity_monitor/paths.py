"""Filesystem paths used by the file integrity monitor."""

from __future__ import annotations

import os

PLUGIN_DIR = os.path.dirname(__file__)
DATABASE_PATH = os.path.join(PLUGIN_DIR, "file_integrity_monitor.db")
LEGACY_CONFIG_PATH = os.path.join(PLUGIN_DIR, "config.json")
LEGACY_BASELINE_PATH = os.path.join(PLUGIN_DIR, "baseline.json")
