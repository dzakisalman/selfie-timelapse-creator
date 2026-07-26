from __future__ import annotations
from dataclasses import dataclass


@dataclass
class FaceLandmarks:
    """
    Abstraksi hasil deteksi wajah — tidak menyimpan tipe MediaPipe.
    Semua koordinat dalam pixel (bukan normalized).
    Dengan abstraksi ini, FaceAligner tidak perlu tahu tentang MediaPipe;
    jika suatu hari diganti InsightFace, hanya FaceDetector yang berubah.
    """

    left_eye_center:  tuple[float, float]           # pixel (x, y)
    right_eye_center: tuple[float, float]           # pixel (x, y)
    nose_tip:         tuple[float, float]           # pixel (x, y)
    mouth_center:     tuple[float, float]           # pixel (x, y)
    bounding_box:     tuple[float, float, float, float]  # x, y, w, h  (pixel)

    image_width:  int
    image_height: int

    @property
    def eyes_midpoint(self) -> tuple[float, float]:
        lx, ly = self.left_eye_center
        rx, ry = self.right_eye_center
        return ((lx + rx) / 2, (ly + ry) / 2)

    @property
    def eye_distance(self) -> float:
        import math
        lx, ly = self.left_eye_center
        rx, ry = self.right_eye_center
        return math.sqrt((rx - lx) ** 2 + (ry - ly) ** 2)
