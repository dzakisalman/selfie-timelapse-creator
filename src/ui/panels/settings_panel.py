from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QGroupBox, QSizePolicy,
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

    def _apply_to_settings(self) -> None:
        _, mode = self._ALIGNMENT_MODES[self.combo_alignment.currentIndex()]
        self._settings.alignment_mode = mode

        _, res = self._RESOLUTIONS[self.combo_resolution.currentIndex()]
        self._settings.resolution = res

        self._settings.fps = self._FPS_OPTIONS[self.combo_fps.currentIndex()]
        self._settings.frames_per_image = self._FRAMES_PER_IMAGE[self.combo_frames.currentIndex()]

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

        self._apply_to_settings()
