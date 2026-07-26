from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QProgressBar,
    QFileDialog, QFrame, QSizePolicy,
)

from core.video_renderer import VideoRenderWorker, QUALITY_PRESETS, estimate_duration
from models.project_settings import ProjectSettings
from models.photo_item import PhotoItem

if TYPE_CHECKING:
    from core.face_aligner import FaceAligner
    from core.crop_processor import CropProcessor
    from renderers.overlay_renderer import OverlayRenderer


class ExportDialog(QDialog):
    """
    Modal dialog untuk konfigurasi dan eksekusi export video.

    Flow:
      [Pilih path] → [Pilih kualitas] → [Lihat estimasi] →
      [Start Export] → [Progress + ETA] → [Done / Error]
    """

    def __init__(
        self,
        photo_items:      list[PhotoItem],
        settings:         ProjectSettings,
        face_aligner:     "FaceAligner",
        crop_proc:        "CropProcessor",
        overlay_renderer: "OverlayRenderer",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._items            = photo_items
        self._settings         = settings
        self._face_aligner     = face_aligner
        self._crop_proc        = crop_proc
        self._overlay_renderer = overlay_renderer
        self._worker: VideoRenderWorker | None = None
        self._start_time: float = 0.0

        self.setWindowTitle("Export MP4")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(24, 20, 24, 20)

        # Title
        title = QLabel("Export Timelapse Video")
        title.setObjectName("appTitle")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #e8eaf6; background:transparent;")
        lay.addWidget(title)

        lay.addWidget(self._divider())

        # Summary
        s = self._settings
        n = len(self._items)
        faces = sum(1 for x in self._items if x.status == "done")
        dur   = estimate_duration(self._items, s)
        summary = QLabel(
            f"📷  {n} photos  ·  {faces} with face  ·  "
            f"🎬  {s.resolution[0]}×{s.resolution[1]}  @  {s.fps} fps\n"
            f"⏱  Estimated duration: {dur:.1f} s  "
            f"({int(dur//60):02d}:{int(dur%60):02d})"
        )
        summary.setObjectName("mutedLabel")
        summary.setStyleSheet("color: #9ba3b8; font-size: 12px; background:transparent;")
        lay.addWidget(summary)

        lay.addWidget(self._divider())

        # Output path
        lay.addWidget(self._field_label("Output File"))
        path_row = QHBoxLayout()
        self.edit_path = QLineEdit(str(self._settings.output_path))
        self.edit_path.setPlaceholderText("Choose output path…")
        btn_browse = QPushButton("Browse")
        btn_browse.setObjectName("outlineButton")
        btn_browse.setFixedWidth(80)
        btn_browse.clicked.connect(self._browse)
        path_row.addWidget(self.edit_path)
        path_row.addWidget(btn_browse)
        lay.addLayout(path_row)

        # Quality
        lay.addWidget(self._field_label("Quality Preset"))
        self.combo_quality = QComboBox()
        for label, crf, preset in QUALITY_PRESETS:
            self.combo_quality.addItem(label)
        self.combo_quality.setCurrentIndex(1)  # Balanced default
        lay.addWidget(self.combo_quality)

        lay.addWidget(self._divider())

        # Progress (hidden at start)
        self.lbl_status = QLabel("Ready to export")
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_status.setStyleSheet("background:transparent;")
        lay.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        lay.addWidget(self.progress_bar)

        self.lbl_eta = QLabel("")
        self.lbl_eta.setStyleSheet("color: #636b82; font-size: 11px; background:transparent;")
        self.lbl_eta.hide()
        lay.addWidget(self.lbl_eta)

        lay.addWidget(self._divider())

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("outlineButton")
        self.btn_cancel.clicked.connect(self._on_cancel)

        self.btn_start = QPushButton("⬇  Start Export")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.clicked.connect(self._on_start)

        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_start)
        lay.addLayout(btn_row)

    # ── Slots ──────────────────────────────────────────────────────────
    def _browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Video As", self.edit_path.text(),
            "MP4 Video (*.mp4)"
        )
        if path:
            if not path.endswith(".mp4"):
                path += ".mp4"
            self.edit_path.setText(path)

    def _on_start(self) -> None:
        output_path = Path(self.edit_path.text().strip())
        if not output_path.parent.exists():
            self.lbl_status.setText("⚠  Output folder does not exist.")
            self.lbl_status.setStyleSheet("color: #e74c3c; background:transparent;")
            return

        self._settings.output_path = output_path
        _, crf, preset = QUALITY_PRESETS[self.combo_quality.currentIndex()]

        self._set_exporting(True)
        self._start_time = time.time()

        self._worker = VideoRenderWorker(
            items=self._items,
            settings=self._settings,
            output_path=output_path,
            face_aligner=self._face_aligner,
            crop_proc=self._crop_proc,
            overlay_renderer=self._overlay_renderer,
            crf=crf,
            preset=preset,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_cancel(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(500)
            self._set_exporting(False)
            self.lbl_status.setText("Export cancelled.")
        else:
            self.reject()

    def _on_progress(self, current: int, total: int, eta: float) -> None:
        pct = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        elapsed = time.time() - self._start_time
        self.lbl_status.setText(
            f"Rendering {current} / {total} photos…  ({pct}%)"
        )
        if eta > 0:
            m, s = divmod(int(eta), 60)
            self.lbl_eta.setText(f"ETA: {m:02d}:{s:02d}")

    def _on_finished(self, path: str) -> None:
        self.progress_bar.setValue(100)
        self.lbl_status.setStyleSheet("color: #2ecc71; background:transparent;")
        self.lbl_status.setText(f"✓  Export complete!")

        # Replace Start/Cancel with Open File / Close
        self.btn_start.setText("Open Folder")
        self.btn_start.clicked.disconnect()
        self.btn_start.clicked.connect(lambda: os.startfile(str(Path(path).parent)))
        self.btn_cancel.setText("Close")

    def _on_failed(self, msg: str) -> None:
        self._set_exporting(False)
        self.lbl_status.setStyleSheet("color: #e74c3c; background:transparent;")
        self.lbl_status.setText(f"⚠  {msg[:120]}")

    # ── Helpers ────────────────────────────────────────────────────────
    def _set_exporting(self, active: bool) -> None:
        self.btn_start.setEnabled(not active)
        self.edit_path.setEnabled(not active)
        self.combo_quality.setEnabled(not active)
        self.progress_bar.setVisible(active)
        self.lbl_eta.setVisible(active)
        if active:
            self.btn_cancel.setText("Stop")
            self.progress_bar.setValue(0)
        else:
            self.btn_cancel.setText("Cancel")

    @staticmethod
    def _field_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        return lbl

    @staticmethod
    def _divider() -> QFrame:
        d = QFrame()
        d.setObjectName("divider")
        return d

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(500)
        super().closeEvent(event)
