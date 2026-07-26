from __future__ import annotations

import cv2
import numpy as np


class CropProcessor:
    """
    Crop frame ke ukuran output yang tepat.
    Terpisah dari FaceAligner sehingga rasio crop (1:1, 9:16, 16:9)
    dapat diubah tanpa menyentuh logika alignment.

    Karena warpAffine sudah menghasilkan frame berukuran output_size,
    modul ini berfungsi sebagai safety net dan titik ekstensi
    (misal padding, letterbox, dll di versi mendatang).
    """

    @staticmethod
    def crop(frame: np.ndarray, output_size: tuple[int, int]) -> np.ndarray:
        """
        Pastikan frame memiliki ukuran persis output_size (W, H).
        Jika sudah benar, langsung return tanpa salinan.
        """
        target_w, target_h = output_size
        fh, fw = frame.shape[:2]

        if fw == target_w and fh == target_h:
            return frame

        # Center-crop jika frame lebih besar
        x0 = max(0, (fw - target_w) // 2)
        y0 = max(0, (fh - target_h) // 2)
        cropped = frame[y0 : y0 + target_h, x0 : x0 + target_w]

        # Resize jika masih tidak pas (fallback)
        ch, cw = cropped.shape[:2]
        if cw != target_w or ch != target_h:
            cropped = cv2.resize(cropped, (target_w, target_h),
                                 interpolation=cv2.INTER_LANCZOS4)
        return cropped
