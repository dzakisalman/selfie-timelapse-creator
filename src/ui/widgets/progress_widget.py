from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QProgressBar, QSizePolicy,
)


class ProgressWidget(QWidget):
    """
    Bottom bar — progress bar, status label, dan tombol Export.
    """

    exportClicked  = Signal()
    cancelClicked  = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("bottomBar")
        self.setFixedHeight(60)
        self._build_ui()
        self._connect_signals()
        self.set_idle()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # Status + progress stacked vertically
        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("statusLabel")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.hide()

        info_col.addWidget(self.lbl_status)
        info_col.addWidget(self.progress_bar)

        layout.addLayout(info_col, stretch=1)

        # Buttons
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("dangerButton")
        self.btn_cancel.setFixedHeight(38)
        self.btn_cancel.setMinimumWidth(90)
        self.btn_cancel.hide()

        self.btn_export = QPushButton("⬇  Export MP4")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.setFixedHeight(38)
        self.btn_export.setMinimumWidth(140)
        self.btn_export.setEnabled(False)

        layout.addWidget(self.btn_cancel)
        layout.addWidget(self.btn_export)

    def _connect_signals(self) -> None:
        self.btn_export.clicked.connect(self.exportClicked)
        self.btn_cancel.clicked.connect(self.cancelClicked)

    # ── Public API ─────────────────────────────────────────────────────
    def set_idle(self) -> None:
        self.lbl_status.setText("Ready")
        self.progress_bar.hide()
        self.btn_cancel.hide()
        self.btn_export.setEnabled(False)

    def set_ready(self, photo_count: int) -> None:
        """Call when photos are loaded and ready to export."""
        self.lbl_status.setText(f"{photo_count} photo{'s' if photo_count != 1 else ''} loaded")
        self.progress_bar.hide()
        self.btn_cancel.hide()
        self.btn_export.setEnabled(True)

    def set_processing(self, message: str = "Processing…") -> None:
        self.lbl_status.setText(message)
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)   # indeterminate
        self.btn_export.setEnabled(False)
        self.btn_cancel.show()

    def set_progress(self, current: int, total: int, message: str = "") -> None:
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.progress_bar.show()
        pct = int(current / total * 100) if total > 0 else 0
        self.lbl_status.setText(message or f"Processing {current} / {total}  ({pct}%)")
        self.btn_cancel.show()
        self.btn_export.setEnabled(False)

    def set_done(self, message: str = "Export complete!") -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.show()
        self.lbl_status.setText(message)
        self.btn_cancel.hide()
        self.btn_export.setEnabled(True)

    def set_error(self, message: str) -> None:
        self.lbl_status.setText(f"⚠  {message}")
        self.lbl_status.setStyleSheet("color: #e74c3c;")
        self.progress_bar.hide()
        self.btn_cancel.hide()
        self.btn_export.setEnabled(True)
