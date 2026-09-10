"""tiny optional helpers for using wmlinksfromhell with Pywikibot."""

from __future__ import annotations

from typing import Any, Optional

from .metadata import MetadataStore
from .parser import WMCode, parse


def parse_page(page: Any, metadata: Optional[MetadataStore] = None) -> WMCode:
    """parse page.text using the Pywikibot Page as source context."""
    return parse(page.text, source=page, metadata=metadata)
