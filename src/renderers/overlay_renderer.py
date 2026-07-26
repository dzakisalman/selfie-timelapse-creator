from __future__ import annotations

from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtGui import (
    QColor, QFont, QFontMetrics, QImage,
    QPainter, QPainterPath, QPen, QBrush,
)

from models.photo_item import PhotoItem
from models.project_settings import ProjectSettings
from utils.age_calculator import calculate_age


class OverlayRenderer:
    """
    Render teks overlay (tanggal, umur) ke atas frame BGR.

    Thread-safe: menggunakan QPainter pada QImage (bukan QPixmap/QWidget).
    Dapat dipanggil dari PreviewWorker thread maupun main thread.

    Strategi rendering:
    - Outline: QPainterPath → stroke (clean, anti-aliased)
    - Shadow: QPainterPath digeser sedikit, semi-transparan
    - Main text: QPainterPath → fill
    """

    def render(
        self,
        frame:      np.ndarray,
        photo_item: PhotoItem,
        settings:   ProjectSettings,
    ) -> np.ndarray:
        """
        Return frame baru dengan overlay teks (kalau overlay aktif).
        Frame original tidak dimodifikasi.
        """
        if not settings.show_date and not settings.show_age:
            return frame

        lines = self._build_lines(photo_item, settings)
        if not lines:
            return frame

        return self._paint(frame, lines, settings)

    # ── Build text lines ───────────────────────────────────────────────
    @staticmethod
    def _build_lines(item: PhotoItem, s: ProjectSettings) -> list[str]:
        lines: list[str] = []
        if s.show_date:
            try:
                lines.append(item.date_used.strftime(s.date_format))
            except Exception:
                lines.append(str(item.date_used.year))
        if s.show_age and s.birth_date:
            age = calculate_age(s.birth_date, item.date_used.date())
            lines.append(f"Age: {age}")
        return lines

    # ── Core paint (QPainter on QImage — thread-safe) ─────────────────
    @staticmethod
    def _paint(frame: np.ndarray, lines: list[str], s: ProjectSettings) -> np.ndarray:
        h, w = frame.shape[:2]

        # BGR → RGB → QImage (make a writable copy so data stays alive)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy()
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)

        # ── Font ───────────────────────────────────────────────────────
        qfont = QFont(s.font_family, s.font_size)
        qfont.setWeight(QFont.Weight.Bold)
        fm = QFontMetrics(qfont)

        line_h = fm.height()
        spacing = max(4, s.font_size // 6)
        total_h = line_h * len(lines) + spacing * (len(lines) - 1)
        max_w = max(fm.horizontalAdvance(ln) for ln in lines)

        # ── Anchor position ────────────────────────────────────────────
        ax, ay = OverlayRenderer._anchor(s, w, h, max_w, total_h)

        # ── Paint ──────────────────────────────────────────────────────
        painter = QPainter(qimg)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        for i, line in enumerate(lines):
            ly = ay + i * (line_h + spacing) + line_h  # baseline y
            lx = ax + (max_w - fm.horizontalAdvance(line)) / 2  # center each line

            path = QPainterPath()
            path.addText(lx, ly, qfont, line)

            # Shadow
            if s.shadow_enabled:
                sd = max(2, s.font_size // 20)
                shadow_path = QPainterPath()
                shadow_path.addText(lx + sd, ly + sd, qfont, line)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 0, 0, 140))
                painter.drawPath(shadow_path)

            # Outline
            if s.outline_enabled and s.outline_thickness > 0:
                or_, og, ob = s.outline_color
                pen = QPen(QColor(or_, og, ob))
                pen.setWidth(s.outline_thickness * 2)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)

            # Fill (main text)
            tr, tg, tb = s.text_color
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(tr, tg, tb))
            painter.drawPath(path)

        painter.end()

        # QImage → BGR numpy
        ptr = qimg.constBits()
        result_rgb = np.array(ptr, dtype=np.uint8).reshape(h, w, 3)
        return cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)

    @staticmethod
    def _anchor(
        s: ProjectSettings,
        img_w: int, img_h: int,
        text_w: int, text_h: int,
    ) -> tuple[float, float]:
        """Hitung posisi top-left anchor untuk blok teks."""
        margin = max(20, img_h // 40)

        preset = s.overlay_position_preset
        if preset == "bottom_center":
            x = (img_w - text_w) / 2
            y = img_h - text_h - margin
        elif preset == "top_center":
            x = (img_w - text_w) / 2
            y = margin
        elif preset == "bottom_left":
            x = margin
            y = img_h - text_h - margin
        elif preset == "bottom_right":
            x = img_w - text_w - margin
            y = img_h - text_h - margin
        elif preset == "custom":
            x = s.overlay_custom_x * img_w - text_w / 2
            y = s.overlay_custom_y * img_h - text_h / 2
        else:
            x = (img_w - text_w) / 2
            y = img_h - text_h - margin

        return x, y
