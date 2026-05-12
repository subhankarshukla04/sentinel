"""Input validation. Boundary check; rejects garbage before it reaches the engines."""
from typing import Tuple


class ValidationError(ValueError):
    pass


def clean_name(name: str | None) -> str:
    if not name or not isinstance(name, str):
        raise ValidationError("project name is required")
    cleaned = " ".join(name.strip().split())
    if len(cleaned) < 3:
        raise ValidationError("project name must be at least 3 characters")
    if len(cleaned) > 200:
        raise ValidationError("project name must be at most 200 characters")
    return cleaned


def clean_coord(lat, lng) -> Tuple[float, float]:
    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        raise ValidationError("latitude and longitude must be numeric")
    if not (-90.0 <= lat_f <= 90.0):
        raise ValidationError(f"latitude {lat_f} out of range [-90, 90]")
    if not (-180.0 <= lng_f <= 180.0):
        raise ValidationError(f"longitude {lng_f} out of range [-180, 180]")
    return lat_f, lng_f


def clean_country(country: str | None) -> str | None:
    if not country:
        return None
    if not isinstance(country, str):
        return None
    cleaned = country.strip()
    if not cleaned:
        return None
    if len(cleaned) > 100:
        return None
    return cleaned
