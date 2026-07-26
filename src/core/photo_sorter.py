from __future__ import annotations

import re
from models.photo_item import PhotoItem


def _natural_key(s: str) -> list:
    """Sort key untuk string yang mengandung angka (natural sort)."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", s)]


def sort_photos(items: list[PhotoItem], mode: str) -> list[PhotoItem]:
    """
    Urutkan daftar foto berdasarkan mode.

    mode:
      'exif_date'    — EXIF date (foto tanpa EXIF ke belakang)
      'filename'     — Natural sort nama file
      'date_modified'— Last modified timestamp
    """
    if mode == "exif_date":
        return sorted(
            items,
            key=lambda x: (x.exif_date is None, x.date_used),
        )
    elif mode == "filename":
        return sorted(items, key=lambda x: _natural_key(x.filename))
    elif mode == "date_modified":
        return sorted(items, key=lambda x: x.modified_date)
    return list(items)
