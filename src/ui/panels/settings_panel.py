from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QGroupBox, QSizePolicy, QSlider,
)

from models.project_settings import ProjectSettings


class SettingsPanel(QWidget):
    """
    Sidebar kanan — konfigurasi output video.
    Memancarkan signal settingsChanged setiap kali ada perubahan.
    """

    settingsChanged = Signal()

    _RESOLUTIONS = [
        ("1080 × 1920  (Portrait 9:16)", (1080, 1920)),
        ("1080 × 1080  (Square 1:1)",    (1080, 1080)),
        ("1920 × 1080  (Landscape 16:9)",(1920, 1080)),
    ]
    _FPS_OPTIONS         = [24, 25, 30, 50, 60]
    _FRAMES_PER_IMAGE    = [1, 2, 3, 4]
    _ALIGNMENT_MODES     = [
        ("Eyes  (recommended)", "eyes"),
        ("Face bounding box",   "face"),
    ]

    # Zoom: slider stores integer 50–300 (= 0.50× – 3.00×), step 5
    _ZOOM_MIN   = 50    # 0.50×
    _ZOOM_MAX   = 300   # 3.00×
    _ZOOM_DEF   = 100   # 1.00×
    _ZOOM_STEP  = 5

    def __init__(self, settings: ProjectSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._build_ui()
        self._connect_signals()
        self._load_from_settings()

    # ── Build UI ───────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        layout.addWidget(self._build_alignment_group())
        layout.addWidget(self._build_output_group())
        layout.addStretch()

    def _build_alignment_group(self) -> QGroupBox:
        group = QGroupBox("ALIGNMENT")
        inner = QVBoxLayout(group)
        inner.setSpacing(8)

        inner.addWidget(self._field_label("Mode"))
        self.combo_alignment = QComboBox()
        for label, _ in self._ALIGNMENT_MODES:
            self.combo_alignment.addItem(label)
        inner.addWidget(self.combo_alignment)

        # ── Zoom Slider ──────────────────────────────────────────────
        inner.addWidget(self._field_label("Zoom"))

        # Header row: label on left, value on right
        zoom_header = QHBoxLayout()
        zoom_header.setContentsMargins(0, 0, 0, 0)
        lbl_out = QLabel("Zoom Out")
        lbl_out.setObjectName("mutedLabel")
        lbl_out.setStyleSheet("color: #636b82; font-size: 11px; background:transparent;")
        self.lbl_zoom_value = QLabel("1.00×")
        self.lbl_zoom_value.setStyleSheet(
            "color: #6c63ff; font-size: 12px; font-weight: 600; background:transparent;"
        )
        self.lbl_zoom_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_in = QLabel("Zoom In")
        lbl_in.setObjectName("mutedLabel")
        lbl_in.setStyleSheet("color: #636b82; font-size: 11px; background:transparent;")
        zoom_header.addWidget(lbl_out)
        zoom_header.addStretch()
        zoom_header.addWidget(self.lbl_zoom_value)
        zoom_header.addStretch()
        zoom_header.addWidget(lbl_in)
        inner.addLayout(zoom_header)

        self.slider_zoom = QSlider(Qt.Orientation.Horizontal)
        self.slider_zoom.setRange(self._ZOOM_MIN, self._ZOOM_MAX)
        self.slider_zoom.setSingleStep(self._ZOOM_STEP)
        self.slider_zoom.setPageStep(self._ZOOM_STEP * 2)
        self.slider_zoom.setValue(self._ZOOM_DEF)
        self.slider_zoom.setTickPosition(QSlider.TickPosition.NoTicks)
        self.slider_zoom.setToolTip("Zoom level (0.50× – 3.00×). Center is always the face/eyes.")
        inner.addWidget(self.slider_zoom)

        # ── Background fill color ────────────────────────────────────
        inner.addWidget(self._field_label("Background (zoom out)"))
        self.combo_bg_color = QComboBox()
        self.combo_bg_color.addItem("■  Black", "black")
        self.combo_bg_color.addItem("□  White", "white")
        inner.addWidget(self.combo_bg_color)

        return group

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("OUTPUT")
        inner = QVBoxLayout(group)
        inner.setSpacing(8)

        # Resolution
        inner.addWidget(self._field_label("Resolution"))
        self.combo_resolution = QComboBox()
        for label, _ in self._RESOLUTIONS:
            self.combo_resolution.addItem(label)
        inner.addWidget(self.combo_resolution)

        # FPS + Frames per image side by side
        row = QHBoxLayout()
        row.setSpacing(8)

        col_fps = QVBoxLayout()
        col_fps.addWidget(self._field_label("FPS"))
        self.combo_fps = QComboBox()
        for fps in self._FPS_OPTIONS:
            self.combo_fps.addItem(str(fps))
        col_fps.addWidget(self.combo_fps)
        row.addLayout(col_fps)

        col_frames = QVBoxLayout()
        col_frames.addWidget(self._field_label("Frames / photo"))
        self.combo_frames = QComboBox()
        for f in self._FRAMES_PER_IMAGE:
            self.combo_frames.addItem(f"{f} fr")
        col_frames.addWidget(self.combo_frames)
        row.addLayout(col_frames)

        inner.addLayout(row)

        # Duration hint
        self.lbl_duration_hint = QLabel()
        self.lbl_duration_hint.setObjectName("mutedLabel")
        self.lbl_duration_hint.setStyleSheet("color: #636b82; font-size: 11px;")
        inner.addWidget(self.lbl_duration_hint)

        return group

    @staticmethod
    def _field_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        return lbl

    # ── Signals ────────────────────────────────────────────────────────
    def _connect_signals(self) -> None:
        self.combo_alignment.currentIndexChanged.connect(self._apply_to_settings)
        self.combo_resolution.currentIndexChanged.connect(self._apply_to_settings)
        self.combo_fps.currentIndexChanged.connect(self._apply_to_settings)
        self.combo_frames.currentIndexChanged.connect(self._apply_to_settings)
        self.slider_zoom.valueChanged.connect(self._on_zoom_changed)
        self.combo_bg_color.currentIndexChanged.connect(self._apply_to_settings)

    def _on_zoom_changed(self, value: int) -> None:
        zoom = value / 100.0
        self.lbl_zoom_value.setText(f"{zoom:.2f}×")
        self._apply_to_settings()

    def _apply_to_settings(self) -> None:
        _, mode = self._ALIGNMENT_MODES[self.combo_alignment.currentIndex()]
        self._settings.alignment_mode = mode

        _, res = self._RESOLUTIONS[self.combo_resolution.currentIndex()]
        self._settings.resolution = res

        self._settings.fps = self._FPS_OPTIONS[self.combo_fps.currentIndex()]
        self._settings.frames_per_image = self._FRAMES_PER_IMAGE[self.combo_frames.currentIndex()]

        self._settings.zoom_level = self.slider_zoom.value() / 100.0
        self._settings.zoom_bg_color = self.combo_bg_color.currentData()

        # Update hint
        ms = round(self._settings.video_duration_per_image * 1000)
        fps_label = self._settings.fps
        frames_label = self._settings.frames_per_image
        self.lbl_duration_hint.setText(
            f"Each photo shown for {ms} ms  ({frames_label} fr @ {fps_label} fps)"
        )

        self.settingsChanged.emit()

    def _load_from_settings(self) -> None:
        """Populate widgets from current settings (initial sync)."""
        s = self._settings

        for i, (_, m) in enumerate(self._ALIGNMENT_MODES):
            if m == s.alignment_mode:
                self.combo_alignment.setCurrentIndex(i)

        for i, (_, r) in enumerate(self._RESOLUTIONS):
            if r == s.resolution:
                self.combo_resolution.setCurrentIndex(i)

        if s.fps in self._FPS_OPTIONS:
            self.combo_fps.setCurrentIndex(self._FPS_OPTIONS.index(s.fps))

        if s.frames_per_image in self._FRAMES_PER_IMAGE:
            self.combo_frames.setCurrentIndex(self._FRAMES_PER_IMAGE.index(s.frames_per_image))

        # Restore zoom slider
        zoom_int = int(round(s.zoom_level * 100))
        zoom_int = max(self._ZOOM_MIN, min(self._ZOOM_MAX, zoom_int))
        self.slider_zoom.setValue(zoom_int)
        self.lbl_zoom_value.setText(f"{s.zoom_level:.2f}×")

        # Restore bg color
        for i in range(self.combo_bg_color.count()):
            if self.combo_bg_color.itemData(i) == s.zoom_bg_color:
                self.combo_bg_color.setCurrentIndex(i)
                break

        self._apply_to_settings()
