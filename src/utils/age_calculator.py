from __future__ import annotations

from datetime import date


def calculate_age(birthdate: date, photo_date: date) -> int:
    """
    Hitung umur penuh dalam tahun pada tanggal foto.
    Mengurangi 1 tahun jika ulang tahun belum terjadi pada tahun tersebut.
    """
    years = photo_date.year - birthdate.year
    # Belum ulang tahun di tahun ini → kurangi 1
    if (photo_date.month, photo_date.day) < (birthdate.month, birthdate.day):
        years -= 1
    return max(0, years)


def age_label(birthdate: date, photo_date: date) -> str:
    """Return string seperti 'Age: 21'."""
    return f"Age: {calculate_age(birthdate, photo_date)}"
