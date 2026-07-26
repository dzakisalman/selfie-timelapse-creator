from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal, Optional


@dataclass
class ProjectSettings:
    """
    Single source of truth untuk seluruh konfigurasi project.
    Hampir semua modul menerima ProjectSettings daripada 15 parameter terpisah.
    """

    # ── Output ────────────────────────────────────────────────────────────
    resolution: tuple[int, int] = (1080, 1920)   # Width x Height
    fps: int = 25
    frames_per_image: int = 2
    output_path: Path = field(default_factory=lambda: Path.home() / "timelapse_output.mp4")

    # ── Sorting ───────────────────────────────────────────────────────────
    sorting_mode: Literal["exif_date", "filename", "date_modified"] = "exif_date"

    # ── Alignment ─────────────────────────────────────────────────────────
    alignment_mode: Literal["eyes", "face"] = "eyes"

    # ── Overlay — Date ────────────────────────────────────────────────────
    show_date: bool = False
    date_format: str = "%B %Y"          # e.g. "May 2024"

    # ── Overlay — Age ─────────────────────────────────────────────────────
    show_age: bool = False
    birth_date: Optional[date] = None

    # ── Overlay — Text Style ──────────────────────────────────────────────
    font_family: str = "Segoe UI"
    font_size: int = 48
    text_color: tuple[int, int, int] = (255, 255, 255)    # RGB
    outline_enabled: bool = True
    outline_thickness: int = 2
    outline_color: tuple[int, int, int] = (0, 0, 0)       # RGB
    shadow_enabled: bool = False

    # ── Overlay — Position ────────────────────────────────────────────────
    overlay_position_preset: Literal[
        "bottom_center", "top_center", "bottom_left", "bottom_right", "custom"
    ] = "bottom_center"
    overlay_custom_x: float = 0.5      # normalized 0.0 – 1.0
    overlay_custom_y: float = 0.88

    # ── Helpers ───────────────────────────────────────────────────────────
    @property
    def width(self) -> int:
        return self.resolution[0]

    @property
    def height(self) -> int:
        return self.resolution[1]

    @property
    def video_duration_per_image(self) -> float:
        """Durasi satu foto dalam detik."""
        return self.frames_per_image / self.fps

    @property
    def resolution_label(self) -> str:
        w, h = self.resolution
        return f"{w} × {h}"


# Module-level constant — used by SettingsPanel to populate dropdowns
RESOLUTION_PRESETS: list[tuple[str, tuple[int, int]]] = [
    ("1080 × 1920  (Portrait 9:16)", (1080, 1920)),
    ("1080 × 1080  (Square 1:1)",    (1080, 1080)),
    ("1920 × 1080  (Landscape 16:9)",(1920, 1080)),
]
