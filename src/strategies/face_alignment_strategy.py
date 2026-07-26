from __future__ import annotations

import numpy as np
import cv2

from models.face_landmarks import FaceLandmarks
from strategies.alignment_strategy import AlignmentStrategy


# Bounding box wajah mengisi FACE_FILL_RATIO × output_height (zoom 1.0)
FACE_FILL_RATIO = 0.65


class FaceAlignmentStrategy(AlignmentStrategy):
    """
    Alignment berdasarkan bounding box wajah.
    Tidak melakukan rotasi — hanya scale + translate agar
    wajah berada di tengah frame dengan ukuran yang konsisten.

    Cocok untuk foto profil / saat kepala tidak banyak bergerak.
    """

    def compute_matrix(
        self,
        landmarks: FaceLandmarks,
        output_size: tuple[int, int],
        zoom_level: float = 1.0,
    ) -> np.ndarray:
        out_w, out_h = output_size

        bx, by, bw, bh = landmarks.bounding_box
        if bw < 1 or bh < 1:
            # Fallback: identity
            return np.eye(2, 3, dtype=np.float64)

        bbox_cx = bx + bw / 2
        bbox_cy = by + bh / 2

        # ── Scale agar bbox height = FACE_FILL_RATIO × output_height × zoom ──
        scale = (out_h * FACE_FILL_RATIO * zoom_level) / bh

        # ── Affine: scale only (no rotation), pivot = bbox center ─────
        M = cv2.getRotationMatrix2D((bbox_cx, bbox_cy), 0.0, scale)

        # ── Translate bbox center → output center ─────────────────────
        M[0, 2] += out_w / 2 - bbox_cx
        M[1, 2] += out_h / 2 - bbox_cy

        return M.astype(np.float64)
