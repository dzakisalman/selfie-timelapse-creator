from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional


@dataclass
class PhotoItem:
    path: Path
    filename: str
    exif_date: Optional[datetime]
    modified_date: datetime
    date_used: datetime          # exif_date ?? modified_date
    landmarks: Optional[Any] = None         # FaceLandmarks (Tahap 3)
    alignment_result: Optional[Any] = None  # AlignmentResult (Tahap 3)
    status: Literal["pending","processing","done","no_face","error"] = "pending"
    error_msg: str = ""

    @property
    def date_label(self) -> str:
        return self.date_used.strftime("%d %b %Y")

    @property
    def date_label_overlay(self) -> str:
        return self.date_used.strftime("%B %Y")

    @property
    def date_source(self) -> str:
        return "EXIF" if self.exif_date else "Modified"

    @property
    def status_icon(self) -> str:
        return {"pending":"·","processing":"⟳","done":"✓","no_face":"⚠","error":"✗"}.get(self.status,"·")
