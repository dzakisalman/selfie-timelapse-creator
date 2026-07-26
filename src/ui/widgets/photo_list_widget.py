from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QSizePolicy,
)


class PhotoListItem(QListWidgetItem):
    """List item yang menyimpan path dan metadata foto."""

    def __init__(self, filename: str, date_str: str,
                 status: str = "pending",
                 thumbnail: QPixmap | None = None) -> None:
        super().__init__()
        self.filename = filename
        self.date_str = date_str
        self.status   = status
        self._build(thumbnail)

    def _build(self, thumbnail: QPixmap | None) -> None:
        if thumbnail:
            self.setIcon(QIcon(thumbnail))
        else:
            # Placeholder gray icon
            ph = QPixmap(60, 60)
            ph.fill(QColor("#242838"))
            self.setIcon(QIcon(ph))

        status_icon = {
            "pending":    "⋯",
            "processing": "⟳",
            "done":       "✓",
            "no_face":    "⚠",
            "error":      "✗",
        }.get(self.status, "⋯")

        self.setText(f"{status_icon}  {self.filename}\n    {self.date_str}")
        self.setSizeHint(QWidget().sizeHint())   # let delegate size it


class PhotoListWidget(QWidget):
    """
    Panel kiri — scrollable daftar foto dengan thumbnail.
    Di Tahap 2 akan terhubung ke PhotoImporter.
    """

    photoSelected = Signal(int)   # index in list

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header row
        header = QWidget()
        header.setStyleSheet("background-color: #0f1117; padding: 0;")
        header.setFixedHeight(36)
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(12, 0, 12, 0)

        self.lbl_section = QLabel("PHOTOS")
        self.lbl_section.setObjectName("sectionTitle")

        self.lbl_count = QLabel("0 photos")
        self.lbl_count.setObjectName("photoCount")
        self.lbl_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        hlay.addWidget(self.lbl_section)
        hlay.addStretch()
        hlay.addWidget(self.lbl_count)

        # List
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QWidget().sizeHint())   # set below
        from PySide6.QtCore import QSize
        self.list_widget.setIconSize(QSize(56, 56))
        self.list_widget.setSpacing(1)
        self.list_widget.setUniformItemSizes(False)

        # Empty state
        self.lbl_empty = QLabel(
            "No photos yet\n\nDrop a folder or use\n\"Add Folder\" above"
        )
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty.setStyleSheet(
            "color: #3d4263; font-size: 12px; background: #1a1d27;"
        )

        layout.addWidget(header)
        layout.addWidget(self.lbl_empty, stretch=1)
        layout.addWidget(self.list_widget, stretch=1)
        self.list_widget.hide()

    def _connect_signals(self) -> None:
        self.list_widget.currentRowChanged.connect(self.photoSelected)

    # ── Public API ─────────────────────────────────────────────────────
    def add_item(self, filename: str, date_str: str,
                 status: str = "pending",
                 thumbnail: QPixmap | None = None) -> PhotoListItem:
        if self.lbl_empty.isVisible():
            self.lbl_empty.hide()
            self.list_widget.show()

        item = PhotoListItem(filename, date_str, status, thumbnail)
        self.list_widget.addItem(item)
        self._update_count()
        return item

    def clear_all(self) -> None:
        self.list_widget.clear()
        self.list_widget.hide()
        self.lbl_empty.show()
        self._update_count()

    def update_item_status(self, index: int, status: str) -> None:
        item = self.list_widget.item(index)
        if item and isinstance(item, PhotoListItem):
            item.status = status
            icon = {"done": "✓", "no_face": "⚠", "error": "✗",
                    "processing": "⟳", "pending": "⋯"}.get(status, "⋯")
            parts = item.text().split("  ", 1)
            if len(parts) == 2:
                item.setText(f"{icon}  {parts[1]}")

    def update_thumbnail(self, index: int, pixmap: "QPixmap") -> None:
        """Perbarui thumbnail item ke-index setelah ThumbnailWorker selesai."""
        item = self.list_widget.item(index)
        if item:
            from PySide6.QtGui import QIcon
            item.setIcon(QIcon(pixmap))

    def count(self) -> int:
        return self.list_widget.count()

    def photo_items_indices(self) -> list[int]:
        return list(range(self.list_widget.count()))

    def _update_count(self) -> None:
        n = self.list_widget.count()
        self.lbl_count.setText(f"{n} photo{'s' if n != 1 else ''}")
