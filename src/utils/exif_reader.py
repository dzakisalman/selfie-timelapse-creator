from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

_EXIF_FORMAT = "%Y:%m:%d %H:%M:%S"
_EXIF_CAPABLE = {".jpg", ".jpeg", ".tiff", ".tif", ".webp"}


def read_exif_date(path: Path) -> Optional[datetime]:
    """
    Baca DateTimeOriginal (36867) > DateTimeDigitized (36868) > DateTime (306)
    dari EXIF foto menggunakan Pillow.
    Return None jika tidak ada atau error.
    """
    if path.suffix.lower() not in _EXIF_CAPABLE:
        return None
    try:
        from PIL import Image
        with Image.open(path) as img:
            exif = img._getexif()
            if not exif:
                return None
            for tag_id in (36867, 36868, 306):
                val = exif.get(tag_id)
                if val:
                    try:
                        return datetime.strptime(val.strip(), _EXIF_FORMAT)
                    except ValueError:
                        continue
    except Exception:
        pass
    return None


def parse_date_from_filename(filename: str) -> Optional[datetime]:
    """
    Coba ekstrak tanggal dari nama file.
    Pattern yang didukung:
      YYYY-MM-DD, YYYY_MM_DD, YYYYMMDD (mis. IMG_20240515_...)
    """
    stem = Path(filename).stem

    # YYYY-MM-DD or YYYY_MM_DD
    m = re.search(r'(\d{4})[_\-](\d{2})[_\-](\d{2})', stem)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                return datetime(y, mo, d)
            except ValueError:
                pass

    # YYYYMMDD (8 digit berurutan, mis. 20240515)
    m = re.search(r'(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)', stem)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                return datetime(y, mo, d)
            except ValueError:
                pass

    return None


def resolve_date(path: Path) -> tuple[Optional[datetime], datetime]:
    """
    Return (exif_date, date_used).
    date_used = exif_date ?? filename_date ?? modified_date
    """
    import os
    exif_date = read_exif_date(path)
    modified  = datetime.fromtimestamp(os.path.getmtime(path))
    date_used = exif_date or parse_date_from_filename(path.name) or modified
    return exif_date, date_used
