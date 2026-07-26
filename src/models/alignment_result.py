from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class AlignmentResult:
    """
    Hasil face alignment untuk satu foto.
    transform_matrix: 2x3 affine matrix yang dipakai.
    aligned_frame: output warpAffine (sebelum crop) — None jika belum di-compute.
    """

    transform_matrix: np.ndarray          # shape (2, 3)
    aligned_frame:    Optional[np.ndarray] # BGR, sama ukuran output_size
    success:          bool
    error_msg:        str = ""
