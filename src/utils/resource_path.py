from __future__ import annotations
import sys
from pathlib import Path


def resource_path(relative: str | Path) -> Path:
    """
    Resolve path ke asset yang benar baik saat development maupun
    setelah di-bundle oleh PyInstaller (sys._MEIPASS).

    Contoh:
        model = resource_path("assets/models/face_landmarker.task")
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller bundle: aset di-extract ke _MEIPASS
        base = Path(sys._MEIPASS)
    else:
        # Development: satu level di atas utils/ → src/
        base = Path(__file__).resolve().parent.parent

    return base / relative
