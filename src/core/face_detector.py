from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from models.face_landmarks import FaceLandmarks
from models.photo_item import PhotoItem
from utils.resource_path import resource_path

# ── MediaPipe landmark indices ─────────────────────────────────────────
# Indeks ini hanya ada di file ini — tidak bocor ke modul lain.
_LEFT_IRIS_CENTER  = 468   # tersedia di model 478-point
_RIGHT_IRIS_CENTER = 473
_LEFT_EYE_OUTER   = 33
_LEFT_EYE_INNER   = 133
_RIGHT_EYE_OUTER  = 263
_RIGHT_EYE_INNER  = 362
_NOSE_TIP         = 4
_MOUTH_LEFT       = 61
_MOUTH_RIGHT      = 291

_MODEL_RELATIVE = Path("assets") / "models" / "face_landmarker.task"


def _create_landmarker(model_path: Path):
    """
    Buat FaceLandmarker baru — harus dipanggil dari thread yang akan
    menggunakannya. MediaPipe/TFLite memiliki thread-affinity di Windows.
    """
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision

    if not model_path.exists():
        raise FileNotFoundError(
            f"MediaPipe model not found: {model_path}\n"
            "Letakkan face_landmarker.task di src/assets/models/"
        )

    base_opts = mp_python.BaseOptions(
        model_asset_path=str(model_path)
    )
    opts = mp_vision.FaceLandmarkerOptions(
        base_options=base_opts,
        num_faces=1,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )
    return mp_vision.FaceLandmarker.create_from_options(opts)


def _extract_landmarks(detector, image_path: Path) -> Optional[FaceLandmarks]:
    """
    Jalankan deteksi pada satu gambar dan return FaceLandmarks.
    Return None jika tidak ada wajah atau error.
    """
    import mediapipe as mp

    try:
        mp_image = mp.Image.create_from_file(str(image_path))
    except Exception:
        bgr = cv2.imread(str(image_path))
        if bgr is None:
            return None
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb.astype(np.uint8),
        )

    try:
        result = detector.detect(mp_image)
    except Exception:
        return None

    if not result.face_landmarks:
        return None

    lms = result.face_landmarks[0]
    W, H = mp_image.width, mp_image.height

    def px(idx: int) -> tuple[float, float]:
        lm = lms[idx]
        return (lm.x * W, lm.y * H)

    def avg(*indices: int) -> tuple[float, float]:
        pts = [px(i) for i in indices]
        return (
            sum(p[0] for p in pts) / len(pts),
            sum(p[1] for p in pts) / len(pts),
        )

    num_lm = len(lms)
    if num_lm >= 478:
        left_eye  = px(_LEFT_IRIS_CENTER)
        right_eye = px(_RIGHT_IRIS_CENTER)
    else:
        left_eye  = avg(_LEFT_EYE_OUTER, _LEFT_EYE_INNER)
        right_eye = avg(_RIGHT_EYE_OUTER, _RIGHT_EYE_INNER)

    nose  = px(_NOSE_TIP)
    mouth = avg(_MOUTH_LEFT, _MOUTH_RIGHT)

    xs = [lm.x * W for lm in lms[:468]]
    ys = [lm.y * H for lm in lms[:468]]
    x0, y0 = min(xs), min(ys)
    x1, y1 = max(xs), max(ys)

    return FaceLandmarks(
        left_eye_center  = left_eye,
        right_eye_center = right_eye,
        nose_tip         = nose,
        mouth_center     = mouth,
        bounding_box     = (x0, y0, x1 - x0, y1 - y0),
        image_width      = W,
        image_height     = H,
    )


class FaceDetector:
    """
    Wrapper MediaPipe FaceLandmarker (Tasks API).

    PENTING: MediaPipe/TFLite di Windows memiliki thread-affinity.
    FaceLandmarker harus dibuat DAN dipanggil dari thread yang sama.

    Kelas ini membuat FaceLandmarker secara lazy di thread yang pertama
    kali memanggil detect(). Jangan gunakan satu instance FaceDetector
    dari dua thread berbeda secara concurrent — gunakan instance terpisah
    atau gunakan DetectionWorker yang membuat detector sendiri.

    Hasil deteksi di-cache per path.
    """

    def __init__(self, model_path: Optional[Path] = None) -> None:
        self._model_path = model_path or resource_path(_MODEL_RELATIVE)
        self._detector   = None
        self._cache: dict[Path, Optional[FaceLandmarks]] = {}

    def detect(self, image_path: Path) -> Optional[FaceLandmarks]:
        """Detect wajah dari path foto. Return None jika tidak ada wajah."""
        if image_path in self._cache:
            return self._cache[image_path]

        if self._detector is None:
            self._detector = _create_landmarker(self._model_path)

        result = _extract_landmarks(self._detector, image_path)
        self._cache[image_path] = result
        return result

    def invalidate_cache(self, image_path: Optional[Path] = None) -> None:
        if image_path:
            self._cache.pop(image_path, None)
        else:
            self._cache.clear()

    def close(self) -> None:
        """Release MediaPipe resources."""
        if self._detector is not None:
            try:
                self._detector.close()
            except Exception:
                pass
            self._detector = None


class DetectionWorker(QThread):
    """
    Background thread untuk face detection pada seluruh foto.

    KUNCI: Membuat FaceLandmarker sendiri di dalam run() sehingga
    model TFLite di-init DAN dipanggil dari thread yang sama.
    Ini menghindari crash thread-affinity di Windows.
    """

    progress      = Signal(int, int)   # current, total
    itemProcessed = Signal(int, bool)  # index, has_face
    finished      = Signal(int, int)   # total_faces, total_photos

    def __init__(
        self,
        model_path: Path,
        items: list[PhotoItem],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._model_path = model_path
        self._items      = items
        self._cancelled  = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        import traceback
        import sys

        total      = len(self._items)
        face_count = 0

        # ── Buat detector DI DALAM thread ini ────────────────────────
        try:
            detector = _create_landmarker(self._model_path)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            for i, item in enumerate(self._items):
                item.status    = "error"
                item.error_msg = str(e)
                self.itemProcessed.emit(i, False)
                self.progress.emit(i + 1, total)
            self.finished.emit(0, total)
            return

        for i, item in enumerate(self._items):
            if self._cancelled:
                break
            try:
                landmarks = _extract_landmarks(detector, item.path)
                item.landmarks = landmarks
                has_face = landmarks is not None

                if has_face:
                    item.status = "done"
                    face_count += 1
                else:
                    item.status = "no_face"

            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                item.status    = "error"
                item.error_msg = str(e)
                has_face       = False

            self.itemProcessed.emit(i, has_face)
            self.progress.emit(i + 1, total)

        # ── Cleanup ──────────────────────────────────────────────────
        try:
            detector.close()
        except Exception:
            pass

        self.finished.emit(face_count, total)

