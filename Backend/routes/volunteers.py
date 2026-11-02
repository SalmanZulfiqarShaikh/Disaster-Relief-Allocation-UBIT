
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from routes import store

router = APIRouter(tags=["volunteers"])


@router.get("/api/volunteers")
def list_volunteers() -> List[Dict[str, Any]]:
    rows = store.select("volunteers")
    rows.sort(key=lambda row: (str(row.get("name") or "").lower(), int(row.get("id") or 0)))
    return [
        {
            "id": row.get("id"),
            "name": row.get("name"),
            "phone": row.get("phone"),
            "status": row.get("status"),
            "zone_ids": row.get("zone_ids") or [],
            "capabilities": row.get("capabilities") or [],
            "lat": row.get("lat"),
            "lng": row.get("lng"),
            "is_demo": bool(row.get("is_demo")),
        }
        for row in rows
    ]
