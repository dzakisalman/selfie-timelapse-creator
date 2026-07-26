from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QFrame,
)


class PreviewArea(QLabel):
    """
    Canvas utama preview — menampilkan frame hasil alignment + overlay.
    Mendukung drag-and-drop untuk memindahkan posisi teks overlay.
    """

    overlayPositionChanged = Signal(float, float)   # normalized x, y

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewArea")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #080a10; border-radius: 4px;")

        self._overlay_drag_active = False
        self._overlay_enabled = False   # set True saat ada overlay untuk di-drag
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self.clear()
        placeholder = QLabel("No photos loaded\nAdd photos to get started →", self)
        placeholder.setObjectName("previewPlaceholder")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(
            "color: #3d4263; font-size: 14px; background: transparent;"
        )
        placeholder.resize(self.size())

    def set_frame(self, pixmap: QPixmap) -> None:
        """Tampilkan frame hasil alignment."""
        # Clear placeholder children
        for child in self.children():
            if isinstance(child, QLabel):
                child.deleteLater()

        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def clear_frame(self) -> None:
        self.clear()
        self._show_placeholder()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pixmap() and not self.pixmap().isNull():
            # Re-scale on resize
            self.set_frame(self.pixmap())
        else:
            for child in self.children():
                if isinstance(child, QLabel):
                    child.resize(self.size())

    # ── Overlay drag support ───────────────────────────────────────────
    def enable_overlay_drag(self, enabled: bool) -> None:
        self._overlay_enabled = enabled
        self.setCursor(
            Qt.CursorShape.OpenHandCursor if enabled else Qt.CursorShape.ArrowCursor
        )

    def mousePressEvent(self, event):
        if self._overlay_enabled and event.button() == Qt.MouseButton.LeftButton:
            self._overlay_drag_active = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._overlay_drag_active:
            w, h = self.width(), self.height()
            nx = max(0.0, min(1.0, event.position().x() / w))
            ny = max(0.0, min(1.0, event.position().y() / h))
            self.overlayPositionChanged.emit(nx, ny)

    def mouseReleaseEvent(self, event):
        if self._overlay_drag_active:
            self._overlay_drag_active = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)


class PreviewPanel(QWidget):
    """
    Panel tengah — preview frame + navigasi foto.
    Di Tahap 1 hanya menampilkan placeholder dan navigasi UI.
    Implementasi penuh di Tahap 4.
    """

    frameNavigated       = Signal(int)   # current index
    overlayMoved         = Signal(float, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewContainer")
        self._total_photos = 0
        self._current_index = 0
        self._build_ui()
        self._connect_signals()

    # ── Build UI ───────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Preview canvas
        self.preview_area = PreviewArea()
        layout.addWidget(self.preview_area, stretch=1)

        # Navigation bar
        nav_bar = QWidget()
        nav_bar.setStyleSheet("background-color: #0d1020; border-top: 1px solid #1f2235;")
        nav_bar.setFixedHeight(52)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(12, 6, 12, 6)
        nav_layout.setSpacing(10)

        self.btn_prev = QPushButton("‹")
        self.btn_prev.setObjectName("navButton")
        self.btn_prev.setToolTip("Previous photo (←)")
        self.btn_prev.setEnabled(False)

        self.lbl_counter = QLabel("–  /  –")
        self.lbl_counter.setObjectName("frameCounter")
        self.lbl_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_next = QPushButton("›")
        self.btn_next.setObjectName("navButton")
        self.btn_next.setToolTip("Next photo (→)")
        self.btn_next.setEnabled(False)

        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_counter)
        nav_layout.addWidget(self.btn_next)
        nav_layout.addStretch()

        layout.addWidget(nav_bar)

    def _connect_signals(self) -> None:
        self.btn_prev.clicked.connect(self._go_prev)
        self.btn_next.clicked.connect(self._go_next)
        self.preview_area.overlayPositionChanged.connect(self.overlayMoved)

    # ── Public API ─────────────────────────────────────────────────────
    def set_photo_count(self, count: int) -> None:
        self._total_photos = count
        self._current_index = 0 if count > 0 else -1
        self._update_nav()

    def show_frame(self, pixmap: QPixmap, index: int) -> None:
        self._current_index = index
        self.preview_area.set_frame(pixmap)
        self._update_nav()

    def clear(self) -> None:
        self._total_photos = 0
        self._current_index = 0
        self.preview_area.clear_frame()
        self._update_nav()

    # ── Private ────────────────────────────────────────────────────────
    def _go_prev(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            self._update_nav()
            self.frameNavigated.emit(self._current_index)

    def _go_next(self) -> None:
        if self._current_index < self._total_photos - 1:
            self._current_index += 1
            self._update_nav()
            self.frameNavigated.emit(self._current_index)

    def _update_nav(self) -> None:
        total = self._total_photos
        idx   = self._current_index

        if total == 0:
            self.lbl_counter.setText("–  /  –")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
        else:
            self.lbl_counter.setText(f"{idx + 1}  /  {total}")
            self.btn_prev.setEnabled(idx > 0)
            self.btn_next.setEnabled(idx < total - 1)
