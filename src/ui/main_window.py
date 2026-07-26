from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QPixmap, QImage, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSplitter, QScrollArea, QFileDialog, QFrame,
    QMessageBox,
)

from models.project_settings import ProjectSettings
from models.photo_item import PhotoItem
from core.photo_importer import ImportWorker, ThumbnailWorker, scan_files
from core.photo_sorter import sort_photos
from core.face_detector import FaceDetector, DetectionWorker
from core.face_aligner import FaceAligner
from core.crop_processor import CropProcessor
from core.preview_worker import PreviewWorker
from renderers.overlay_renderer import OverlayRenderer
from ui.panels.import_panel   import ImportPanel
from ui.panels.settings_panel import SettingsPanel
from ui.panels.overlay_panel  import OverlayPanel
from ui.panels.preview_panel  import PreviewPanel
from ui.widgets.photo_list_widget import PhotoListWidget
from ui.widgets.progress_widget   import ProgressWidget
from ui.widgets.export_dialog     import ExportDialog


class MainWindow(QMainWindow):
    """
    Single-window: [ Header ] / [ Left | Preview | Right ] / [ Bottom ]
    """

    # Delay (ms) sebelum preview di-refresh setelah settings berubah
    _PREVIEW_DEBOUNCE_MS = 280

    def __init__(self) -> None:
        super().__init__()
        self._settings = ProjectSettings()

        # ── App state ──────────────────────────────────────────────────
        self._photo_items:      list[PhotoItem]          = []
        self._current_index:    int                      = -1

        # ── Workers ───────────────────────────────────────────────────
        self._import_worker:    Optional[ImportWorker]    = None
        self._thumb_worker:     Optional[ThumbnailWorker] = None
        self._detection_worker: Optional[DetectionWorker] = None
        self._preview_worker:   Optional[PreviewWorker]   = None

        # ── Core processors (shared, lazy-init inside each) ───────────
        self._face_detector    = FaceDetector()
        self._face_aligner     = FaceAligner()
        self._crop_proc        = CropProcessor()
        self._overlay_renderer = OverlayRenderer()

        # ── Preview debounce timer ─────────────────────────────────────
        self._preview_debounce = QTimer(self)
        self._preview_debounce.setSingleShot(True)
        self._preview_debounce.timeout.connect(self._refresh_preview)

        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()

    # ── Window ─────────────────────────────────────────────────────────
    def _setup_window(self) -> None:
        self.setWindowTitle("Selfie Timelapse Creator")
        self.setMinimumSize(1200, 750)
        self.resize(1440, 900)

    # ── Build UI ───────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(root)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_content(), stretch=1)
        layout.addWidget(self._build_bottom_bar())

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("headerWidget")
        header.setFixedHeight(52)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(10)

        icon = QLabel("🎞")
        icon.setStyleSheet("font-size: 22px; background: transparent;")
        title = QLabel("Selfie Timelapse Creator")
        title.setObjectName("appTitle")
        sep = QLabel("·")
        sep.setStyleSheet("color: #2d3245; background: transparent; font-size: 18px;")
        sub = QLabel("Face-aligned timelapse, fully offline")
        sub.setObjectName("appSubtitle")

        lay.addWidget(icon)
        lay.addWidget(title)
        lay.addWidget(sep)
        lay.addWidget(sub)
        lay.addStretch()

        by = QLabel("by Allen")
        by.setStyleSheet(
            "color: #3d4263; font-size: 11px; font-style: italic; background: transparent;"
        )
        lay.addWidget(by)

        return header

    def _build_content(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(self._build_left_sidebar())
        splitter.addWidget(self._build_preview_column())
        splitter.addWidget(self._build_right_sidebar())

        splitter.setSizes([240, 9999, 290])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        return splitter

    def _build_left_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("leftSidebar")
        sidebar.setMinimumWidth(220)
        sidebar.setMaximumWidth(320)
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.import_panel = ImportPanel()
        self.photo_list   = PhotoListWidget()

        lay.addWidget(self.import_panel)
        div = QFrame(); div.setObjectName("divider")
        lay.addWidget(div)
        lay.addWidget(self.photo_list, stretch=1)
        return sidebar

    def _build_preview_column(self) -> QWidget:
        container = QWidget()
        container.setObjectName("previewContainer")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.preview_panel = PreviewPanel()
        lay.addWidget(self.preview_panel)
        return container

    def _build_right_sidebar(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("rightSidebar")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(240)
        scroll.setMaximumWidth(340)

        content = QWidget()
        content.setObjectName("rightSidebar")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 6, 0, 12)
        lay.setSpacing(0)

        self.settings_panel = SettingsPanel(self._settings)
        self.overlay_panel  = OverlayPanel(self._settings)
        lay.addWidget(self.settings_panel)
        lay.addWidget(self.overlay_panel)
        lay.addStretch()

        scroll.setWidget(content)
        return scroll

    def _build_bottom_bar(self) -> ProgressWidget:
        self.progress_widget = ProgressWidget()
        return self.progress_widget

    # ── Signal connections ─────────────────────────────────────────────
    def _connect_signals(self) -> None:
        # Import
        self.import_panel.addFolderClicked.connect(self._on_add_folder)
        self.import_panel.addPhotosClicked.connect(self._on_add_photos)
        self.import_panel.folderDropped.connect(self._on_folder_dropped)
        self.import_panel.filesDropped.connect(self._on_files_dropped)
        self.import_panel.sortModeChanged.connect(self._on_sort_changed)

        # Navigation
        self.photo_list.photoSelected.connect(self._on_photo_selected)
        self.preview_panel.frameNavigated.connect(self._on_frame_navigated)
        self.preview_panel.overlayMoved.connect(self._on_overlay_moved)

        # Settings — alignment/output change invalidates cache; overlay does not
        self.settings_panel.settingsChanged.connect(self._on_output_settings_changed)
        self.overlay_panel.overlayChanged.connect(self._on_overlay_changed)

        # Export
        self.progress_widget.exportClicked.connect(self._on_export)
        self.progress_widget.cancelClicked.connect(self._on_cancel)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Left"),  self).activated.connect(
            self.preview_panel.btn_prev.click)
        QShortcut(QKeySequence("Right"), self).activated.connect(
            self.preview_panel.btn_next.click)

    # ═══════════════════════════════════════════════════════════════════
    # IMPORT
    # ═══════════════════════════════════════════════════════════════════
    def _on_add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Photo Folder")
        if folder:
            self._start_import(scan_files(Path(folder)), clear=True)

    def _on_add_photos(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Photos", "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif)"
        )
        if files:
            self._start_import([Path(f) for f in files], clear=False)

    def _on_folder_dropped(self, folder_path: str) -> None:
        self._start_import(scan_files(Path(folder_path)), clear=True)

    def _on_files_dropped(self, file_paths: list[str]) -> None:
        self._start_import([Path(f) for f in file_paths], clear=False)

    def _start_import(self, paths: list[Path], clear: bool) -> None:
        if not hasattr(self, "_zombie_workers"):
            self._zombie_workers = []
        self._zombie_workers = [w for w in self._zombie_workers if w.isRunning()]

        if self._import_worker and self._import_worker.isRunning():
            self._import_worker.cancel()
            if not self._import_worker.wait(100):
                self._zombie_workers.append(self._import_worker)

        if not paths:
            return

        if clear:
            self._photo_items.clear()
            self._current_index = -1
            self.photo_list.clear_all()
            self.preview_panel.clear()

        self.progress_widget.set_processing(f"Scanning {len(paths)} files…")

        self._import_worker = ImportWorker(paths)
        self._import_worker.progress.connect(self._on_import_progress)
        self._import_worker.itemReady.connect(self._on_item_ready)
        self._import_worker.allLoaded.connect(self._on_all_loaded)
        self._import_worker.start()

    def _cancel_all_workers(self) -> None:
        for w in (self._import_worker, self._thumb_worker,
                  self._detection_worker, self._preview_worker):
            if w and w.isRunning():
                w.cancel()
                w.wait(300)

    # ── Import worker slots ────────────────────────────────────────────
    def _on_import_progress(self, current: int, total: int) -> None:
        self.progress_widget.set_progress(
            current, total, f"Reading metadata… {current} / {total}"
        )

    def _on_item_ready(self, _index: int, item: object) -> None:
        photo: PhotoItem = item  # type: ignore
        self._photo_items.append(photo)
        self.photo_list.add_item(
            filename=photo.filename,
            date_str=f"{photo.date_label}  [{photo.date_source}]",
            status=photo.status,
        )

    def _on_all_loaded(self, items: list) -> None:
        sorted_items = sort_photos(items, self._settings.sorting_mode)
        self._photo_items = sorted_items
        self._rebuild_photo_list()
        self.preview_panel.set_photo_count(len(sorted_items))

        if sorted_items:
            self.progress_widget.set_processing(
                f"Loading thumbnails… 0 / {len(sorted_items)}"
            )
            self._start_thumbnail_worker()
        else:
            self.progress_widget.set_idle()
            QMessageBox.information(
                self, "No Photos Found",
                "No supported image files were found.\n"
                "Supported: JPG, PNG, WEBP, TIFF, BMP"
            )

    # ── Thumbnail worker ───────────────────────────────────────────────
    def _start_thumbnail_worker(self) -> None:
        if not hasattr(self, "_zombie_workers"):
            self._zombie_workers = []
        self._zombie_workers = [w for w in self._zombie_workers if w.isRunning()]

        if self._thumb_worker and self._thumb_worker.isRunning():
            self._thumb_worker.cancel()
            if not self._thumb_worker.wait(100):
                self._zombie_workers.append(self._thumb_worker)

        self._thumb_worker = ThumbnailWorker(self._photo_items)
        self._thumb_worker.thumbnailReady.connect(self._on_thumbnail_ready)
        self._thumb_worker.finished.connect(self._on_thumbnails_done)
        self._thumb_worker.start()

    def _on_thumbnail_ready(self, index: int, jpeg_bytes: bytes) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(jpeg_bytes)
        self.photo_list.update_thumbnail(index, pixmap)
        n = len(self._photo_items)
        self.progress_widget.set_progress(
            index + 1, n, f"Loading thumbnails… {index+1} / {n}"
        )

    def _on_thumbnails_done(self) -> None:
        if self._photo_items:
            self._start_detection()
        else:
            self.progress_widget.set_ready(0)

    # ── Detection worker ───────────────────────────────────────────────
    def _start_detection(self) -> None:
        if not hasattr(self, "_zombie_workers"):
            self._zombie_workers = []
        self._zombie_workers = [w for w in self._zombie_workers if w.isRunning()]

        if self._detection_worker and self._detection_worker.isRunning():
            self._detection_worker.cancel()
            if not self._detection_worker.wait(100):
                self._zombie_workers.append(self._detection_worker)

        n = len(self._photo_items)
        self.progress_widget.set_processing(f"Detecting faces… 0 / {n}")
        self._detection_worker = DetectionWorker(
            self._face_detector._model_path, self._photo_items
        )
        self._detection_worker.progress.connect(self._on_detection_progress)
        self._detection_worker.itemProcessed.connect(self._on_item_detected)
        self._detection_worker.finished.connect(self._on_detection_done)
        self._detection_worker.start()

    def _on_detection_progress(self, current: int, total: int) -> None:
        self.progress_widget.set_progress(
            current, total, f"Detecting faces… {current} / {total}"
        )

    def _on_item_detected(self, index: int, has_face: bool) -> None:
        self.photo_list.update_item_status(index, "done" if has_face else "no_face")

    def _on_detection_done(self, face_count: int, total: int) -> None:
        no_face = total - face_count
        msg = f"{face_count} faces detected"
        if no_face:
            msg += f"  ·  {no_face} skipped (no face)"
        self.progress_widget.set_ready(face_count)
        self.progress_widget.lbl_status.setText(msg)

        # Auto-select first photo with a face (setCurrentRow triggers preview automatically)
        for i, item in enumerate(self._photo_items):
            if item.status == "done":
                self._current_index = i
                self.photo_list.list_widget.setCurrentRow(i)
                break

    # ═══════════════════════════════════════════════════════════════════
    # PREVIEW
    # ═══════════════════════════════════════════════════════════════════
    def _on_photo_selected(self, index: int) -> None:
        if 0 <= index < len(self._photo_items):
            self._current_index = index
            self._request_preview(self._photo_items[index], index)

    def _on_frame_navigated(self, index: int) -> None:
        self._current_index = index
        self.photo_list.list_widget.setCurrentRow(index)
        if 0 <= index < len(self._photo_items):
            self._request_preview(self._photo_items[index], index)

    def _request_preview(self, item: PhotoItem, index: int) -> None:
        """Cancel preview in flight, start new PreviewWorker."""
        if not hasattr(self, "_zombie_workers"):
            self._zombie_workers = []

        # Cleanup dead zombies
        self._zombie_workers = [w for w in self._zombie_workers if w.isRunning()]

        if self._preview_worker and self._preview_worker.isRunning():
            self._preview_worker.cancel()
            # If wait fails, keep a reference so Python GC doesn't destroy the running thread
            if not self._preview_worker.wait(150):
                self._zombie_workers.append(self._preview_worker)

        worker = PreviewWorker(
            item, self._settings,
            self._face_aligner,
            self._crop_proc, self._overlay_renderer,
        )
        worker.frameReady.connect(
            lambda raw, w, h, idx=index: self._on_frame_ready(raw, w, h, idx)
        )
        worker.failed.connect(lambda msg: self._on_preview_failed(msg, index))
        self._preview_worker = worker
        worker.start()

    def _on_frame_ready(self, raw_bytes: bytes, w: int, h: int, index: int) -> None:
        """Convert BGR bytes → QPixmap in main thread, then display."""
        arr = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(h, w, 3)
        import cv2
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg.copy())
        self.preview_panel.show_frame(pixmap, index)

    def _on_preview_failed(self, msg: str, index: int) -> None:
        # Show a placeholder with error text — for now just clear preview
        self.preview_panel.clear()

    def _refresh_preview(self) -> None:
        """Called by debounce timer after settings change."""
        if 0 <= self._current_index < len(self._photo_items):
            self._request_preview(
                self._photo_items[self._current_index],
                self._current_index,
            )

    # ═══════════════════════════════════════════════════════════════════
    # SETTINGS
    # ═══════════════════════════════════════════════════════════════════
    def _on_output_settings_changed(self) -> None:
        """Alignment or resolution changed → invalidate cached alignment."""
        for item in self._photo_items:
            item.alignment_result = None
        self._preview_debounce.start(self._PREVIEW_DEBOUNCE_MS)

    def _on_overlay_changed(self) -> None:
        """Overlay text/style changed — no need to re-align."""
        self._preview_debounce.start(self._PREVIEW_DEBOUNCE_MS)

    # ═══════════════════════════════════════════════════════════════════
    # SORTING
    # ═══════════════════════════════════════════════════════════════════
    def _on_sort_changed(self, mode: str) -> None:
        self._settings.sorting_mode = mode
        if self._photo_items:
            self._photo_items = sort_photos(self._photo_items, mode)
            self._rebuild_photo_list()
            self.preview_panel.set_photo_count(len(self._photo_items))

    def _rebuild_photo_list(self) -> None:
        self.photo_list.clear_all()
        for photo in self._photo_items:
            self.photo_list.add_item(
                filename=photo.filename,
                date_str=f"{photo.date_label}  [{photo.date_source}]",
                status=photo.status,
            )

    # ═══════════════════════════════════════════════════════════════════
    # OVERLAY DRAG
    # ═══════════════════════════════════════════════════════════════════
    def _on_overlay_moved(self, nx: float, ny: float) -> None:
        self._settings.overlay_position_preset = "custom"
        self._settings.overlay_custom_x = nx
        self._settings.overlay_custom_y = ny
        self._preview_debounce.start(self._PREVIEW_DEBOUNCE_MS)

    # ═══════════════════════════════════════════════════════════════════
    # EXPORT (Tahap 6)
    # ═══════════════════════════════════════════════════════════════════
    def _on_export(self) -> None:
        if not self._photo_items:
            return
        dlg = ExportDialog(
            photo_items      = self._photo_items,
            settings         = self._settings,
            face_aligner     = self._face_aligner,
            crop_proc        = self._crop_proc,
            overlay_renderer = self._overlay_renderer,
            parent           = self,
        )
        dlg.exec()

    def _on_cancel(self) -> None:
        self._cancel_all_workers()
        faces = sum(1 for p in self._photo_items if p.status == "done")
        if faces > 0:
            self.progress_widget.set_ready(faces)
        elif self._photo_items:
            self.progress_widget.set_ready(len(self._photo_items))
        else:
            self.progress_widget.set_idle()

    # ── Cleanup ────────────────────────────────────────────────────────
    def closeEvent(self, event) -> None:
        self._preview_debounce.stop()
        self._cancel_all_workers()
        super().closeEvent(event)
