
from __future__ import annotations

import logging
import time
from collections import deque
from threading import Lock
from typing import Any, Deque, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services import assistant, llm

logger = logging.getLogger("safezone.chat")

router = APIRouter(prefix="/api", tags=["chat"])

RATE_LIMIT_MESSAGES = 30
RATE_LIMIT_WINDOW_S = 3600

_hits: Dict[str, Deque[float]] = {}
_hits_lock = Lock()


class ImagePayload(BaseModel):
    base64: str = Field(default="", max_length=8_000_000)
    mimeType: str = Field(default="image/jpeg", max_length=100)


class ChatTurn(BaseModel):
    role: str = Field(default="user", max_length=20)
    text: str = Field(default="", max_length=assistant.MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    message: str = Field(default="", max_length=assistant.MAX_MESSAGE_CHARS)
    history: list[ChatTurn] = Field(default_factory=list)
    image: Optional[ImagePayload] = None


class ChatResponse(BaseModel):
    reply: str


def _caller(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _within_budget(caller: str) -> bool:
    now = time.time()
    with _hits_lock:
        seen = _hits.setdefault(caller, deque())
        while seen and now - seen[0] > RATE_LIMIT_WINDOW_S:
            seen.popleft()
        if len(seen) >= RATE_LIMIT_MESSAGES:
            return False
        seen.append(now)

        if len(_hits) > 5000:
            for key in [k for k, v in _hits.items() if not v]:
                _hits.pop(key, None)
    return True


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    caller = _caller(request)

    if not _within_budget(caller):
        logger.info("Chat rate limit hit by %s", caller)
        raise HTTPException(
            status_code=429,
            detail=(
                "You have reached the message limit for now. "
                "Message SafeZone on WhatsApp if you need help."
            ),
        )

    image: Optional[Dict[str, Any]] = None
    if payload.image and payload.image.base64:
        image = {"base64": payload.image.base64, "mimeType": payload.image.mimeType}

    try:
        answer = assistant.reply(
            payload.message,
            history=[turn.model_dump() for turn in payload.history],
            image=image,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Message was empty.")
    except llm.LLMUnavailable as exc:
        logger.warning("Chat unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=(
                "The assistant is unavailable right now. "
                "Message SafeZone on WhatsApp and someone will see it."
            ),
        )
    except Exception:
        logger.exception("Chat failed for %s", caller)
        raise HTTPException(
            status_code=500,
            detail=(
                "Something went wrong answering that. "
                "Message SafeZone on WhatsApp if you need help."
            ),
        )

    return ChatResponse(reply=answer)
