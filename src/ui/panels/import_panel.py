from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QFrame,
)


class DropZone(QFrame):
    """Drag-and-drop zone untuk foto/folder."""

    folderDropped = Signal(str)   # emitted with folder path
    filesDropped  = Signal(list)  # emitted with list of file paths

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(110)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        icon = QLabel("📁")
        icon.setObjectName("dropZoneIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_text = QLabel("Drop folder or photos here")
        top_text.setObjectName("dropZoneText")
        top_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub_text = QLabel("JPG · PNG · WEBP · TIFF")
        sub_text.setObjectName("dropZoneText")
        sub_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_text.setStyleSheet("color: #4a5068; font-size: 11px;")

        layout.addWidget(icon)
        layout.addWidget(top_text)
        layout.addWidget(sub_text)

    # ── Drag events ────────────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                "QFrame#dropZone { border: 2px dashed #6c63ff;"
                " background-color: rgba(108,99,255,0.08);"
                " border-radius: 10px; }"
            )
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")   # revert to QSS

    def dropEvent(self, event):
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls]
        if not paths:
            return

        import os
        folders = [p for p in paths if os.path.isdir(p)]
        files   = [p for p in paths if os.path.isfile(p)]

        if folders:
            self.folderDropped.emit(folders[0])
        if files:
            self.filesDropped.emit(files)

        event.acceptProposedAction()


class ImportPanel(QWidget):
    """
    Panel kiri atas — import foto dan pilih mode sorting.
    Signals dikomunikasikan ke MainWindow.
    """

    addFolderClicked = Signal()
    addPhotosClicked = Signal()
    sortModeChanged  = Signal(str)   # 'exif_date' | 'filename' | 'date_modified'
    folderDropped    = Signal(str)
    filesDropped     = Signal(list)

    _SORT_MODES = [
        ("EXIF Date (recommended)", "exif_date"),
        ("Filename",                "filename"),
        ("Date Modified",           "date_modified"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(8)

        # Drop zone
        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_add_folder = QPushButton("＋ Folder")
        self.btn_add_folder.setObjectName("outlineButton")
        self.btn_add_folder.setToolTip("Select a folder containing photos")

        self.btn_add_photos = QPushButton("＋ Photos")
        self.btn_add_photos.setObjectName("outlineButton")
        self.btn_add_photos.setToolTip("Select individual photos")

        btn_row.addWidget(self.btn_add_folder)
        btn_row.addWidget(self.btn_add_photos)
        layout.addLayout(btn_row)

        # Sort mode
        sort_label = QLabel("SORT BY")
        sort_label.setObjectName("sectionTitle")

        self.combo_sort = QComboBox()
        for label, _ in self._SORT_MODES:
            self.combo_sort.addItem(label)
        self.combo_sort.setToolTip("Choose how photos are ordered")

        layout.addWidget(sort_label)
        layout.addWidget(self.combo_sort)

    def _connect_signals(self) -> None:
        self.btn_add_folder.clicked.connect(self.addFolderClicked)
        self.btn_add_photos.clicked.connect(self.addPhotosClicked)
        self.drop_zone.folderDropped.connect(self.folderDropped)
        self.drop_zone.filesDropped.connect(self.filesDropped)
        self.combo_sort.currentIndexChanged.connect(self._on_sort_changed)

    def _on_sort_changed(self, index: int) -> None:
        _, mode = self._SORT_MODES[index]
        self.sortModeChanged.emit(mode)

    def set_sort_mode(self, mode: str) -> None:
        for i, (_, m) in enumerate(self._SORT_MODES):
            if m == mode:
                self.combo_sort.setCurrentIndex(i)
                break
