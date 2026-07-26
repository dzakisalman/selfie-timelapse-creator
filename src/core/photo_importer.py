from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from models.photo_item import PhotoItem
from utils.exif_reader import resolve_date

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def scan_files(source: Path | list[Path]) -> list[Path]:
    """
    Kumpulkan semua file foto dari folder (top-level) atau list path.
    Return list path yang sudah difilter berdasarkan ekstensi.
    """
    if isinstance(source, list):
        return [
            Path(p) for p in source
            if Path(p).suffix.lower() in SUPPORTED_EXTENSIONS
        ]

    folder = Path(source)
    if not folder.is_dir():
        return []

    paths = [
        p for p in sorted(folder.iterdir())
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return paths


class ImportWorker(QThread):
    """
    Thread 1 — Scan file dan baca metadata (EXIF, modified date).
    Berjalan di background; tidak menyentuh QPixmap.
    """

    progress    = Signal(int, int)    # current, total
    itemReady   = Signal(int, object) # index, PhotoItem
    allLoaded   = Signal(list)        # list[PhotoItem]
    failed      = Signal(str)         # error message

    def __init__(self, paths: list[Path], parent=None) -> None:
        super().__init__(parent)
        self._paths = paths
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        items: list[PhotoItem] = []
        total = len(self._paths)

        for i, path in enumerate(self._paths):
            if self._cancelled:
                break
            try:
                exif_date, date_used = resolve_date(path)
                modified = datetime.fromtimestamp(os.path.getmtime(path))
                item = PhotoItem(
                    path=path,
                    filename=path.name,
                    exif_date=exif_date,
                    modified_date=modified,
                    date_used=date_used,
                )
                items.append(item)
                self.itemReady.emit(i, item)
            except Exception as e:
                # Skip file yang tidak bisa dibaca
                pass
            self.progress.emit(i + 1, total)

        self.allLoaded.emit(items)


class ThumbnailWorker(QThread):
    """
    Thread 2 — Generate thumbnail JPEG bytes dari setiap foto.
    Berjalan setelah ImportWorker selesai.
    Main thread menerima bytes dan mengkonversi ke QPixmap.
    """

    thumbnailReady = Signal(int, bytes)   # index, JPEG bytes
    finished       = Signal()

    THUMB_SIZE = (60, 60)

    def __init__(self, items: list[PhotoItem], parent=None) -> None:
        super().__init__(parent)
        self._items = items
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            from PIL import Image, ImageOps
            import io
        except ImportError:
            self.finished.emit()
            return

        for i, item in enumerate(self._items):
            if self._cancelled:
                break
            try:
                with Image.open(item.path) as img:
                    # Fix EXIF rotation
                    img = ImageOps.exif_transpose(img)
                    # Convert to RGB (handles RGBA, P, L, etc.)
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    # Center-crop to square then resize
                    img = ImageOps.fit(img, self.THUMB_SIZE, Image.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=80)
                    self.thumbnailReady.emit(i, buf.getvalue())
            except Exception:
                pass  # Biarkan placeholder tetap

        self.finished.emit()
