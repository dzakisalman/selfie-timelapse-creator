from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap


def ndarray_to_qpixmap(arr: np.ndarray) -> QPixmap:
    """
    Konversi BGR numpy array (OpenCV) → QPixmap (Qt).
    HARUS dipanggil dari main thread karena QPixmap tidak thread-safe.
    """
    if arr is None or arr.size == 0:
        return QPixmap()
    rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    bpl = ch * w  # bytes per line
    qimg = QImage(rgb.data, w, h, bpl, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())  # .copy() agar data tidak hilang saat arr GC'd


def scale_qpixmap_to_fit(pixmap: QPixmap, max_w: int, max_h: int) -> QPixmap:
    """Scale pixmap agar muat dalam max_w × max_h dengan mempertahankan aspek rasio."""
    if pixmap.isNull():
        return pixmap
    return pixmap.scaled(
        max_w, max_h,
        aspectRatioMode=1,      # Qt.AspectRatioMode.KeepAspectRatio
        transformMode=1,        # Qt.TransformationMode.SmoothTransformation
    )
