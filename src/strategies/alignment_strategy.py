from __future__ import annotations

from abc import ABC, abstractmethod
import numpy as np

from models.face_landmarks import FaceLandmarks


class AlignmentStrategy(ABC):
    """
    Abstract base untuk strategi face alignment.
    Setiap implementasi menerima FaceLandmarks + output_size
    dan mengembalikan affine matrix 2×3.

    FaceAligner tidak perlu tahu detail implementasi —
    cukup panggil compute_matrix() lalu warpAffine.
    """

    @abstractmethod
    def compute_matrix(
        self,
        landmarks: FaceLandmarks,
        output_size: tuple[int, int],   # (width, height)
    ) -> np.ndarray:
        """Return 2×3 affine matrix (float64)."""
        ...
