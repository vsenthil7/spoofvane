"""Inspection layer — render suspect pages via Bright Data Scraping Browser."""

from .browser import BrightDataInspector, MockInspector, get_inspector

__all__ = ["BrightDataInspector", "MockInspector", "get_inspector"]
