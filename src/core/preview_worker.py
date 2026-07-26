from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from models.photo_item import PhotoItem
from models.project_settings import ProjectSettings

if TYPE_CHECKING:
    from core.face_aligner import FaceAligner
    from core.crop_processor import CropProcessor
    from renderers.overlay_renderer import OverlayRenderer


class PreviewWorker(QThread):
    """
    Background thread untuk menghasilkan satu frame preview.
    Pipeline: load → align (cache hit) → crop → overlay → emit bytes

    Jika item.landmarks sudah terisi (dari DetectionWorker), langsung align.
    Jika belum, skip deteksi (user harus run detection dulu) dan tampilkan
    gambar raw yang di-resize.

    Raw bytes (np.ndarray) di-emit agar konversi QPixmap terjadi di main thread.
    """

    frameReady = Signal(bytes, int, int)  # raw BGR bytes, width, height
    failed     = Signal(str)             # error message

    def __init__(
        self,
        item:             PhotoItem,
        settings:         ProjectSettings,
        face_aligner:     "FaceAligner",
        crop_proc:        "CropProcessor",
        overlay_renderer: "OverlayRenderer",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._item             = item
        self._settings         = settings
        self._face_aligner     = face_aligner
        self._crop_proc        = crop_proc
        self._overlay_renderer = overlay_renderer
        self._cancelled        = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        item = self._item
        W, H = self._settings.width, self._settings.height

        # ── 1. Load image ────────────────────────────────────────────
        img = cv2.imread(str(item.path))
        if img is None:
            self.failed.emit(f"Cannot read: {item.filename}")
            return
        if self._cancelled:
            return

        # ── 2. No landmarks → show raw image rescaled ────────────────
        if item.landmarks is None or item.status == "no_face":
            resized = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
            resized = self._overlay_renderer.render(resized, item, self._settings)
            self._emit_frame(resized)
            return

        if self._cancelled:
            return

        # ── 3. Align (use cache if valid) ────────────────────────────
        ar = item.alignment_result
        if ar and ar.success and ar.aligned_frame is not None:
            frame = ar.aligned_frame
        else:
            result = self._face_aligner.align(img, item.landmarks, self._settings)
            item.alignment_result = result
            if not result.success or result.aligned_frame is None:
                self.failed.emit(result.error_msg or "Alignment failed")
                return
            frame = result.aligned_frame

        if self._cancelled:
            return

        # ── 4. Crop ──────────────────────────────────────────────────
        frame = self._crop_proc.crop(frame, self._settings.resolution)

        # ── 5. Overlay (QPainterPath, thread-safe) ───────────────────
        frame = self._overlay_renderer.render(frame, item, self._settings)

        # ── 6. Emit raw bytes ────────────────────────────────────────
        self._emit_frame(frame)

    def _emit_frame(self, frame: np.ndarray) -> None:
        if self._cancelled:
            return
        h, w = frame.shape[:2]
        self.frameReady.emit(frame.tobytes(), w, h)
