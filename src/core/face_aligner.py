from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from models.face_landmarks import FaceLandmarks
from models.alignment_result import AlignmentResult
from models.project_settings import ProjectSettings
from strategies.eyes_alignment import EyesAlignment
from strategies.face_alignment_strategy import FaceAlignmentStrategy


class FaceAligner:
    """
    Menerapkan AlignmentStrategy ke sebuah gambar menggunakan OpenCV.
    Tidak tahu soal indeks MediaPipe — hanya menerima FaceLandmarks.

    Pipeline:
        FaceLandmarks → strategy.compute_matrix() → cv2.warpAffine → AlignmentResult
    """

    def __init__(self) -> None:
        self._strategies = {
            "eyes": EyesAlignment(),
            "face": FaceAlignmentStrategy(),
        }

    def align(
        self,
        image: np.ndarray,
        landmarks: FaceLandmarks,
        settings: ProjectSettings,
    ) -> AlignmentResult:
        strategy = self._strategies.get(settings.alignment_mode, self._strategies["eyes"])
        out_w, out_h = settings.width, settings.height

        try:
            M = strategy.compute_matrix(landmarks, (out_w, out_h))
            aligned = cv2.warpAffine(
                image, M, (out_w, out_h),
                flags=cv2.INTER_LANCZOS4,
                borderMode=cv2.BORDER_REFLECT,
            )
            return AlignmentResult(transform_matrix=M, aligned_frame=aligned, success=True)

        except Exception as e:
            empty = np.zeros((out_h, out_w, 3), dtype=np.uint8)
            dummy_M = np.eye(2, 3, dtype=np.float64)
            return AlignmentResult(
                transform_matrix=dummy_M,
                aligned_frame=empty,
                success=False,
                error_msg=str(e),
            )
