
from __future__ import annotations

import hmac
import json
import logging
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from core import config
from services import intake, whatsapp

logger = logging.getLogger("safezone.webhook")

router = APIRouter(tags=["webhook"])


@dataclass(frozen=True)
class InboundMessage:

    sender: str
    text: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    location_name: Optional[str] = None


class WhatsAppText(BaseModel):
    model_config = ConfigDict(extra="ignore")

    body: str = ""


class WhatsAppLocation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    name: Optional[str] = None
    address: Optional[str] = None


class WhatsAppMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    sender: str = Field(alias="from")
    type: str
    text: Optional[WhatsAppText] = None
    location: Optional[WhatsAppLocation] = None


class WhatsAppValue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messages: list[Any] = Field(default_factory=list)


class WhatsAppChange(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: WhatsAppValue = Field(default_factory=WhatsAppValue)


class WhatsAppEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    changes: list[WhatsAppChange] = Field(default_factory=list)


class WhatsAppPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entry: list[WhatsAppEntry] = Field(default_factory=list)


@router.get("/webhook/whatsapp")
def verify(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token") or ""
    challenge = params.get("hub.challenge") or ""
    expected = config.WHATSAPP_VERIFY_TOKEN

    if mode == "subscribe" and expected and hmac.compare_digest(token, expected):
        return PlainTextResponse(challenge)

    logger.warning("Rejected webhook verification (mode=%r)", mode)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def receive(request: Request):
    try:
        raw = await request.body()

        if not whatsapp.verify_signature(raw, request.headers.get("x-hub-signature-256")):
            logger.warning("Rejected webhook: invalid X-Hub-Signature-256")
            return {"status": "ignored"}

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("Rejected webhook: body is not valid JSON")
            return {"status": "ignored"}

        if not isinstance(payload, Mapping):
            logger.warning("Rejected webhook: payload is not an object")
            return {"status": "ignored"}

        for message in parse_messages(payload):
            intake.handle_inbound(
                message.sender,
                message.text,
                lat=message.lat,
                lng=message.lng,
                location_name=message.location_name,
            )

    except Exception:
        logger.exception("Webhook processing failed; acknowledged anyway")

    return {"status": "received"}


def parse_messages(payload: Mapping[str, Any]) -> Iterator[InboundMessage]:
    try:
        envelope = WhatsAppPayload.model_validate(payload)
    except ValidationError as exc:
        logger.warning("Ignoring malformed WhatsApp payload: %s", exc.errors()[:2])
        return

    for entry in envelope.entry:
        for change in entry.changes:
            for raw_message in change.value.messages:
                try:
                    message = WhatsAppMessage.model_validate(raw_message)
                except ValidationError:
                    logger.warning("Ignoring a malformed WhatsApp message")
                    continue

                parsed = _flatten(message)
                if parsed is None:
                    logger.info("Ignoring unsupported WhatsApp message type %r", message.type)
                    continue

                yield parsed


def _flatten(message: WhatsAppMessage) -> Optional[InboundMessage]:
    if message.type == "text" and message.text is not None:
        return InboundMessage(sender=message.sender, text=message.text.body)

    if message.type == "location" and message.location is not None:
        lat, lng = message.location.latitude, message.location.longitude
        if not _plausible_coordinates(lat, lng):
            logger.warning("Ignoring a location message with unusable coordinates")
            return None
        label = (message.location.name or message.location.address or "").strip()
        return InboundMessage(
            sender=message.sender,
            text=label,
            lat=lat,
            lng=lng,
            location_name=label or None,
        )

    return None


def _plausible_coordinates(lat: Optional[float], lng: Optional[float]) -> bool:
    if lat is None or lng is None:
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0
