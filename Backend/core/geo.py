
from __future__ import annotations

import math
from typing import Any, Optional, Tuple

EARTH_RADIUS_KM = 6371.0


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return distance_km(lat1, lng1, lat2, lng2) * 1000.0


def coordinates(row: Any) -> Optional[Tuple[float, float]]:
    if row is None:
        return None
    try:
        lat = row.get("lat")
        lng = row.get("lng")
    except AttributeError:
        return None

    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None
