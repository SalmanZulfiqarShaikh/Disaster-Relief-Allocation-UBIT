
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from services import registration

logger = logging.getLogger("safezone.register")

router = APIRouter(tags=["registration"])


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    first_name: str = Field(min_length=1, max_length=80)
    zone_id: Optional[str] = Field(default=None, max_length=60)
    wants_alerts: bool = True


@router.post("/api/register")
def register(body: RegistrationRequest) -> Dict[str, Any]:
    try:
        return registration.create(
            body.first_name,
            body.zone_id,
            wants_alerts=body.wants_alerts,
        )
    except registration.RegistrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/register/{code}")
def registration_status(code: str) -> Dict[str, Any]:
    return registration.status(code)
