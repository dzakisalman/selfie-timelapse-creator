from __future__ import annotations

import math
import numpy as np
import cv2

from models.face_landmarks import FaceLandmarks
from strategies.alignment_strategy import AlignmentStrategy


EYE_Y_RATIO    = 0.37   # Mata berada di 37% dari atas frame
EYE_DIST_RATIO = 0.18   # Jarak antar mata = 18% dari tinggi frame (zoom 1.0)


class EyesAlignment(AlignmentStrategy):
    """
    Alignment berdasarkan posisi kedua mata.
    Paling stabil untuk selfie timelapse — satu pivot point yang konsisten.

    Langkah:
    1. Hitung angle dari garis mata horizontal
    2. Hitung scale agar jarak mata = EYE_DIST_RATIO × output_height × zoom_level
    3. Putar + scale dengan pivot di titik tengah mata
    4. Tambah translasi agar titik tengah mata = (W/2, H × EYE_Y_RATIO)
    """

    def compute_matrix(
        self,
        landmarks: FaceLandmarks,
        output_size: tuple[int, int],
        zoom_level: float = 1.0,
    ) -> np.ndarray:
        out_w, out_h = output_size

        lx, ly = landmarks.left_eye_center
        rx, ry = landmarks.right_eye_center

        # ── 1. Rotation angle ─────────────────────────────────────────
        dx = rx - lx
        dy = ry - ly
        angle_deg = math.degrees(math.atan2(dy, dx))

        # ── 2. Scale (zoom_level multiplier applied here) ─────────────
        actual_dist  = landmarks.eye_distance
        desired_dist = out_h * EYE_DIST_RATIO * zoom_level
        scale = desired_dist / actual_dist if actual_dist > 1.0 else 1.0

        # ── 3. Affine matrix (rotation + scale, pivot = eyes midpoint) ─
        cx, cy = landmarks.eyes_midpoint
        M = cv2.getRotationMatrix2D((cx, cy), angle_deg, scale)

        # ── 4. Translation: move eyes midpoint → canonical position ───
        target_x = out_w / 2
        target_y = out_h * EYE_Y_RATIO
        M[0, 2] += target_x - cx
        M[1, 2] += target_y - cy

        return M.astype(np.float64)
