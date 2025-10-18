"""Scanning helpers for the file integrity monitor."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Iterable

from .types import Inventory


@dataclass(frozen=True)
class ScanResult:
    """Summary of a directory scan."""

    changed: tuple[str, ...]
    deleted: tuple[str, ...]
    new: tuple[str, ...]

    @property
    def has_findings(self) -> bool:
        return any((self.changed, self.deleted, self.new))

    def signature(self) -> str:
        payload = {
            "changed": self.changed,
            "deleted": self.deleted,
            "new": self.new,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def build_inventory(folders: Iterable[str]) -> Inventory:
    inventory: Inventory = {}
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        for root, _, files in os.walk(folder):
            for filename in files:
                path = os.path.join(root, filename)
                try:
                    digest = _hash_file(path)
                except OSError:
                    continue
                inventory[path] = {
                    "hash": digest,
                    "size": os.path.getsize(path),
                    "mtime": os.path.getmtime(path),
                }
    return inventory


def compare_inventories(baseline: Inventory, current: Inventory) -> ScanResult:
    changed: list[str] = []
    deleted: list[str] = []
    new_files: list[str] = []

    for path, info in baseline.items():
        current_info = current.get(path)
        if current_info is None:
            deleted.append(path)
            continue
        if current_info.get("hash") != info.get("hash"):
            changed.append(path)

    for path in current:
        if path not in baseline:
            new_files.append(path)

    return ScanResult(
        tuple(sorted(changed)),
        tuple(sorted(deleted)),
        tuple(sorted(new_files)),
    )


def _hash_file(path: str) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
