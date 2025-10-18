"""State manager for the file integrity monitor dialog."""

from __future__ import annotations

import os
from typing import Iterable, Sequence

from .acknowledgements import clear_acknowledgements
from .persistence import initialize_database, load_baseline, load_config, save_baseline, save_config
from .scanner import ScanResult, build_inventory, compare_inventories
from .types import Inventory


class MonitorController:
    def __init__(self) -> None:
        initialize_database()
        directories, interval, auto_scan = load_config()
        self.directories: list[str] = directories
        self.interval_minutes = interval
        self.auto_scan_enabled = auto_scan
        self.baseline: Inventory = load_baseline()

    # directory management -------------------------------------------------
    def add_directory(self, path: str) -> bool:
        normalized = os.path.abspath(path)
        if normalized in self.directories:
            return False
        self.directories.append(normalized)
        self._persist()
        return True

    def remove_directories(self, paths: Sequence[str]) -> bool:
        target = {os.path.abspath(path) for path in paths}
        original = set(self.directories)
        self.directories = [path for path in self.directories if path not in target]
        removed = original != set(self.directories)
        if removed:
            self._persist()
        return removed

    # settings -------------------------------------------------------------
    def update_interval(self, value: int) -> None:
        self.interval_minutes = max(1, min(value, 24 * 60))
        self._persist()

    def toggle_auto_scan(self, enabled: bool) -> None:
        self.auto_scan_enabled = enabled
        self._persist()

    # baseline -------------------------------------------------------------
    def capture_baseline(self, folders: Iterable[str]) -> Inventory:
        inventory = build_inventory(folders)
        save_baseline(inventory)
        clear_acknowledgements()
        self.baseline = inventory
        return inventory

    def has_baseline(self) -> bool:
        return bool(self.baseline)

    # scanning -------------------------------------------------------------
    def perform_scan(self) -> ScanResult:
        current = build_inventory(self.directories)
        result = compare_inventories(self.baseline, current)
        return result

    # persistence ----------------------------------------------------------
    def _persist(self) -> None:
        save_config(self.directories, self.interval_minutes, self.auto_scan_enabled)
