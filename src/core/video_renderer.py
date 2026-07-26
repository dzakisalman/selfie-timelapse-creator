from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from models.photo_item import PhotoItem
from models.project_settings import ProjectSettings
from utils.resource_path import resource_path

if TYPE_CHECKING:
    from core.face_aligner import FaceAligner
    from core.crop_processor import CropProcessor
    from renderers.overlay_renderer import OverlayRenderer


# ── Quality presets ───────────────────────────────────────────────────
QUALITY_PRESETS: list[tuple[str, int, str]] = [
    ("Fast   (CRF 28, veryfast)",  28, "veryfast"),
    ("Balanced (CRF 23, medium)",  23, "medium"),
    ("Quality (CRF 18, slow)",     18, "slow"),
]


def find_ffmpeg() -> str:
    """Cari FFmpeg: bundled di assets/ → PATH → fallback nama saja."""
    bundled = resource_path(Path("assets") / "ffmpeg" / "ffmpeg.exe")
    if bundled.exists():
        return str(bundled)
    found = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    return found or "ffmpeg"


def estimate_duration(items: list[PhotoItem], settings: ProjectSettings) -> float:
    """Estimasi durasi video dalam detik."""
    return len(items) * settings.frames_per_image / settings.fps


class VideoRenderWorker(QThread):
    """
    Background thread untuk render video via FFmpeg pipe.

    Pipeline per foto:
      load → align (cache hit) → crop → overlay → tulis ke stdin N kali
    """

    progress = Signal(int, int, float)  # current, total, eta_seconds
    finished = Signal(str)              # output path (str)
    failed   = Signal(str)             # error message

    def __init__(
        self,
        items:            list[PhotoItem],
        settings:         ProjectSettings,
        output_path:      Path,
        face_aligner:     "FaceAligner",
        crop_proc:        "CropProcessor",
        overlay_renderer: "OverlayRenderer",
        crf:              int  = 23,
        preset:           str  = "medium",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._items            = items
        self._settings         = settings
        self._output_path      = output_path
        self._face_aligner     = face_aligner
        self._crop_proc        = crop_proc
        self._overlay_renderer = overlay_renderer
        self._crf              = crf
        self._preset           = preset
        self._cancelled        = False

    def cancel(self) -> None:
        self._cancelled = True

    # ── Main render loop ──────────────────────────────────────────────
    def run(self) -> None:
        s         = self._settings
        W, H      = s.width, s.height
        ffmpeg    = find_ffmpeg()
        out_path  = self._output_path
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            ffmpeg, "-y",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{W}x{H}", "-pix_fmt", "bgr24",
            "-r", str(s.fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", self._preset,
            "-crf", str(self._crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out_path),
        ]

        import tempfile
        err_file = tempfile.TemporaryFile()

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=err_file,
            )
        except FileNotFoundError:
            self.failed.emit(
                "FFmpeg not found.\n"
                "Letakkan ffmpeg.exe di assets/ffmpeg/ atau tambahkan ke PATH."
            )
            err_file.close()
            return

        total      = len(self._items)
        start_time = time.time()

        for i, item in enumerate(self._items):
            if self._cancelled:
                proc.stdin.close()
                proc.kill()
                proc.wait()
                err_file.close()
                return

            frame = self._build_frame(item, W, H)
            if frame is None:
                continue

            frame_bytes = frame.tobytes()
            try:
                for _ in range(s.frames_per_image):
                    proc.stdin.write(frame_bytes)
            except BrokenPipeError:
                break  # FFmpeg closed — read stderr below

            # Progress + ETA
            elapsed = time.time() - start_time
            rate    = (i + 1) / elapsed if elapsed > 0 else 0
            eta     = (total - i - 1) / rate if rate > 0 else 0
            self.progress.emit(i + 1, total, eta)

        proc.stdin.close()
        ret = proc.wait()
        
        err_file.seek(0)
        stderr = err_file.read().decode("utf-8", errors="replace")
        err_file.close()

        if ret != 0 and not self._cancelled:
            # Show last 600 chars of FFmpeg stderr (most relevant)
            self.failed.emit(f"FFmpeg error (code {ret}):\n{stderr[-600:]}")
        elif not self._cancelled:
            self.finished.emit(str(out_path))

    # ── Per-frame processing ──────────────────────────────────────────
    def _build_frame(self, item: PhotoItem, W: int, H: int) -> np.ndarray | None:
        img = cv2.imread(str(item.path))
        if img is None:
            return None

        s = self._settings

        if item.status == "no_face" or item.landmarks is None:
            # No face: center-resize to output
            frame = cv2.resize(img, (W, H), interpolation=cv2.INTER_LANCZOS4)
        else:
            # Use cached alignment if available
            ar = item.alignment_result
            if ar and ar.success and ar.aligned_frame is not None:
                frame = ar.aligned_frame
            else:
                result = self._face_aligner.align(img, item.landmarks, s)
                item.alignment_result = result
                frame = result.aligned_frame if result.success else \
                        cv2.resize(img, (W, H), interpolation=cv2.INTER_LANCZOS4)

        frame = self._crop_proc.crop(frame, s.resolution)
        frame = self._overlay_renderer.render(frame, item, s)
        return frame
