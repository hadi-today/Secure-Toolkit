"""Expose the web blueprint for the file integrity monitor."""

from .routes import file_integrity_bp

__all__ = ["file_integrity_bp"]
