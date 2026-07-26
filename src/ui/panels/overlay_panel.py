from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QSpinBox, QComboBox,
    QGroupBox, QDateEdit, QSizePolicy, QColorDialog,
    QFrame,
)
from PySide6.QtCore import QDate

from models.project_settings import ProjectSettings


class ColorButton(QPushButton):
    """Tombol kecil yang menampilkan warna dan membuka QColorDialog saat diklik."""

    colorChanged = Signal(tuple)   # emits (r, g, b)

    def __init__(self, color: tuple[int, int, int] = (255, 255, 255),
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(34, 34)
        self.setToolTip("Click to choose color")
        self._update_style()
        self.clicked.connect(self._pick_color)

    def _update_style(self) -> None:
        r, g, b = self._color
        self.setStyleSheet(
            f"QPushButton {{ background-color: rgb({r},{g},{b});"
            f" border: 1.5px solid #3d4263; border-radius: 6px; }}"
            f"QPushButton:hover {{ border-color: #6c63ff; }}"
        )

    def _pick_color(self) -> None:
        r, g, b = self._color
        initial = QColor(r, g, b)
        chosen = QColorDialog.getColor(initial, self, "Choose Color")
        if chosen.isValid():
            self._color = (chosen.red(), chosen.green(), chosen.blue())
            self._update_style()
            self.colorChanged.emit(self._color)

    def color(self) -> tuple[int, int, int]:
        return self._color

    def set_color(self, rgb: tuple[int, int, int]) -> None:
        self._color = rgb
        self._update_style()


class OverlayPanel(QWidget):
    """
    Sidebar kanan — konfigurasi overlay teks (tanggal, umur, style, posisi).
    Memancarkan signal overlayChanged setiap ada perubahan.
    """

    overlayChanged = Signal()

    _POSITION_PRESETS = [
        ("Bottom Center",  "bottom_center"),
        ("Top Center",     "top_center"),
        ("Bottom Left",    "bottom_left"),
        ("Bottom Right",   "bottom_right"),
        ("Custom",         "custom"),
    ]

    _FONT_FAMILIES = [
        "Segoe UI", "Arial", "Calibri", "Tahoma",
        "Verdana", "Georgia", "Times New Roman", "Courier New",
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

        layout.addWidget(self._build_date_age_group())
        layout.addWidget(self._build_style_group())
        layout.addWidget(self._build_position_group())
        layout.addStretch()

    def _build_date_age_group(self) -> QGroupBox:
        group = QGroupBox("DATE & AGE")
        inner = QVBoxLayout(group)
        inner.setSpacing(8)

        self.chk_show_date = QCheckBox("Show Date")
        inner.addWidget(self.chk_show_date)

        self.chk_show_age = QCheckBox("Show Age")
        inner.addWidget(self.chk_show_age)

        # Birth date input (visible only when show_age is checked)
        self.lbl_birthdate = self._field_label("Date of Birth  (DD/MM/YYYY)")
        self.date_birth = QDateEdit()
        self.date_birth.setDisplayFormat("dd/MM/yyyy")
        self.date_birth.setCalendarPopup(True)
        self.date_birth.setDate(QDate(1995, 1, 1))
        self.lbl_birthdate.hide()
        self.date_birth.hide()

        inner.addWidget(self.lbl_birthdate)
        inner.addWidget(self.date_birth)

        return group

    def _build_style_group(self) -> QGroupBox:
        group = QGroupBox("TEXT STYLE")
        inner = QVBoxLayout(group)
        inner.setSpacing(8)

        # Font family
        inner.addWidget(self._field_label("Font"))
        self.combo_font = QComboBox()
        for f in self._FONT_FAMILIES:
            self.combo_font.addItem(f)
        inner.addWidget(self.combo_font)

        # Font size + text color
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        col_size = QVBoxLayout()
        col_size.addWidget(self._field_label("Size"))
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(12, 200)
        self.spin_font_size.setValue(48)
        self.spin_font_size.setSuffix(" px")
        col_size.addWidget(self.spin_font_size)
        row1.addLayout(col_size)

        col_color = QVBoxLayout()
        col_color.addWidget(self._field_label("Color"))
        self.btn_text_color = ColorButton((255, 255, 255))
        col_color.addWidget(self.btn_text_color)
        row1.addLayout(col_color)
        row1.addStretch()

        inner.addLayout(row1)

        # Outline
        self.chk_outline = QCheckBox("Outline")
        inner.addWidget(self.chk_outline)

        row2 = QHBoxLayout()
        row2.setSpacing(8)

        col_thick = QVBoxLayout()
        col_thick.addWidget(self._field_label("Thickness"))
        self.spin_outline_thick = QSpinBox()
        self.spin_outline_thick.setRange(1, 10)
        self.spin_outline_thick.setValue(2)
        col_thick.addWidget(self.spin_outline_thick)
        row2.addLayout(col_thick)

        col_ocol = QVBoxLayout()
        col_ocol.addWidget(self._field_label("Outline Color"))
        self.btn_outline_color = ColorButton((0, 0, 0))
        col_ocol.addWidget(self.btn_outline_color)
        row2.addLayout(col_ocol)
        row2.addStretch()

        self.outline_detail_widget = QWidget()
        self.outline_detail_widget.setLayout(row2)
        inner.addWidget(self.outline_detail_widget)

        # Shadow
        self.chk_shadow = QCheckBox("Shadow")
        inner.addWidget(self.chk_shadow)

        return group

    def _build_position_group(self) -> QGroupBox:
        group = QGroupBox("POSITION")
        inner = QVBoxLayout(group)
        inner.setSpacing(8)

        self.combo_position = QComboBox()
        for label, _ in self._POSITION_PRESETS:
            self.combo_position.addItem(label)
        inner.addWidget(self.combo_position)

        hint = QLabel("You can also drag the text directly on the preview.")
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #4a5068; font-size: 11px;")
        inner.addWidget(hint)

        return group

    @staticmethod
    def _field_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        return lbl

    # ── Signals ────────────────────────────────────────────────────────
    def _connect_signals(self) -> None:
        self.chk_show_age.toggled.connect(self._toggle_birthdate_visibility)
        self.chk_show_date.toggled.connect(self._apply)
        self.chk_show_age.toggled.connect(self._apply)
        self.date_birth.dateChanged.connect(self._apply)
        self.combo_font.currentIndexChanged.connect(self._apply)
        self.spin_font_size.valueChanged.connect(self._apply)
        self.btn_text_color.colorChanged.connect(self._apply)
        self.chk_outline.toggled.connect(self._apply)
        self.spin_outline_thick.valueChanged.connect(self._apply)
        self.btn_outline_color.colorChanged.connect(self._apply)
        self.chk_shadow.toggled.connect(self._apply)
        self.combo_position.currentIndexChanged.connect(self._apply)

    def _toggle_birthdate_visibility(self, checked: bool) -> None:
        self.lbl_birthdate.setVisible(checked)
        self.date_birth.setVisible(checked)

    def _apply(self, *_) -> None:
        s = self._settings
        s.show_date = self.chk_show_date.isChecked()
        s.show_age  = self.chk_show_age.isChecked()

        if s.show_age:
            qd = self.date_birth.date()
            from datetime import date
            s.birth_date = date(qd.year(), qd.month(), qd.day())

        s.font_family     = self.combo_font.currentText()
        s.font_size       = self.spin_font_size.value()
        s.text_color      = self.btn_text_color.color()
        s.outline_enabled = self.chk_outline.isChecked()
        s.outline_thickness = self.spin_outline_thick.value()
        s.outline_color   = self.btn_outline_color.color()
        s.shadow_enabled  = self.chk_shadow.isChecked()

        _, preset = self._POSITION_PRESETS[self.combo_position.currentIndex()]
        s.overlay_position_preset = preset

        self.overlayChanged.emit()

    def _load_from_settings(self) -> None:
        s = self._settings
        self.chk_show_date.setChecked(s.show_date)
        self.chk_show_age.setChecked(s.show_age)
        self.combo_font.setCurrentText(s.font_family)
        self.spin_font_size.setValue(s.font_size)
        self.btn_text_color.set_color(s.text_color)
        self.chk_outline.setChecked(s.outline_enabled)
        self.spin_outline_thick.setValue(s.outline_thickness)
        self.btn_outline_color.set_color(s.outline_color)
        self.chk_shadow.setChecked(s.shadow_enabled)

        for i, (_, p) in enumerate(self._POSITION_PRESETS):
            if p == s.overlay_position_preset:
                self.combo_position.setCurrentIndex(i)
                break

        self._toggle_birthdate_visibility(s.show_age)
