
from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter

from routes import store

logger = logging.getLogger("safezone.routes.zones")

router = APIRouter(tags=["zones"])


@router.get("/api/zones")
def zones() -> List[Dict[str, Any]]:
    rows = store.select("zones")

    areas = [
        {
            "id": row.get("id"),
            "name": row.get("name"),
            "lat": row.get("lat"),
            "lng": row.get("lng"),
        }
        for row in rows
        if row.get("id") and row.get("name")
    ]

    if not areas:
        logger.warning("No zones in the database. Run: python -m data.seed")

    return sorted(areas, key=lambda area: str(area["name"]).lower())
