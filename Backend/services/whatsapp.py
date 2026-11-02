
from __future__ import annotations

import hashlib
import hmac
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Deque, Optional

import httpx

from core import config
from core.db import execute, get_db
from core.phone import mask, try_normalize

logger = logging.getLogger("safezone.whatsapp")

META_MESSAGES_URL = "https://graph.facebook.com/v26.0/{phone_id}/messages"
MAX_TEXT_LENGTH = 4096

_lock = threading.Lock()
_total_sends = 0
_number_sends: dict[str, Deque[float]] = defaultdict(deque)


def send_message(to: str, text: str) -> bool:
    try:
        return _send_message(to, text)
    except Exception:
        logger.exception("Unexpected failure while sending a message")
        return False


def _send_message(to: str, text: str) -> bool:
    mode = "mock" if config.MOCK_MODE else "live"

    normalized = try_normalize(to)
    if normalized is None:
        logger.warning("Suppressed message to invalid phone %s", mask(str(to)))
        _record(str(to), text, "suppressed", mode, "invalid_phone")
        return False

    if config.KILL_SWITCH:
        logger.warning("Suppressed message to %s: kill switch is on", mask(normalized))
        _record(normalized, text, "suppressed", mode, "kill_switch")
        return False

    if _total_sends >= config.GLOBAL_MESSAGE_CAP:
        logger.warning("Suppressed message to %s: global message cap reached", mask(normalized))
        _record(normalized, text, "suppressed", mode, "global_cap")
        return False

    now = time.monotonic()
    if _rate_limited(normalized, now):
        logger.warning("Suppressed message to %s: per-number rate limit", mask(normalized))
        _record(normalized, text, "suppressed", mode, "rate_limited")
        return False

    if config.ALLOWLIST_ONLY and normalized not in _allowlist():
        logger.warning("Suppressed message to %s: not in DEMO_ALLOWLIST", mask(normalized))
        _record(normalized, text, "suppressed", mode, "not_allowlisted")
        return False

    if not _window_open(normalized):
        logger.warning("Suppressed message to %s: 24h WhatsApp window closed", mask(normalized))
        _record(normalized, text, "suppressed", mode, "window_closed")
        return False

    if config.MOCK_MODE:
        logger.info("MOCK -> %s: %s", mask(normalized), text)
        _note_send(normalized, now)
        _record(normalized, text, "sent", "mock")
        return True

    return _send_live(normalized, text, now)


def _send_live(to: str, text: str, now: float) -> bool:
    if not config.WHATSAPP_TOKEN or not config.WHATSAPP_PHONE_ID:
        logger.error("Cannot send to %s: WhatsApp credentials are missing", mask(to))
        _record(to, text, "failed", "live", "missing_whatsapp_credentials")
        return False

    url = META_MESSAGES_URL.format(phone_id=config.WHATSAPP_PHONE_ID)
    body = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text[:MAX_TEXT_LENGTH]},
    }

    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"},
            json=body,
            timeout=10.0,
        )
    except Exception as exc:
        logger.error("WhatsApp send to %s failed: %s", mask(to), exc)
        _record(to, text, "failed", "live", "network_error")
        return False

    if response.status_code >= 400:
        logger.error(
            "WhatsApp send to %s failed with HTTP %s: %s",
            mask(to),
            response.status_code,
            response.text[:300],
        )
        _record(to, text, "failed", "live", f"http_{response.status_code}")
        return False

    logger.info("Sent to %s", mask(to))
    _note_send(to, now)
    _record(to, text, "sent", "live")
    return True


def verify_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    secret = config.WHATSAPP_APP_SECRET
    if not secret:
        logger.warning("WHATSAPP_APP_SECRET not set; skipping webhook signature verification")
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _allowlist() -> set[str]:
    return {try_normalize(number) or number for number in config.DEMO_ALLOWLIST}


def _rate_limited(phone: str, now: float) -> bool:
    with _lock:
        sends = _number_sends[phone]
        while sends and now - sends[0] > config.PER_NUMBER_RATE_WINDOW_S:
            sends.popleft()
        return len(sends) >= config.PER_NUMBER_RATE_LIMIT


def _note_send(phone: str, now: float) -> None:
    global _total_sends
    with _lock:
        _total_sends += 1
        _number_sends[phone].append(now)


def _window_open(phone: str) -> bool:
    now = datetime.now(timezone.utc)
    try:
        client = get_db()
        found = False
        for table in ("people", "volunteers"):
            result = execute(
                client.table(table).select("window_open_until").eq("phone", phone).limit(5)
            )
            rows = getattr(result, "data", result)
            for row in rows or []:
                found = True
                opened = _parse_timestamp(row.get("window_open_until"))
                if opened is not None and opened > now:
                    return True
        return not found
    except Exception as exc:
        logger.warning("Could not check the 24h window for %s (%s)", mask(phone), exc)
        return True


def _parse_timestamp(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _record(
    to_phone: str,
    text: str,
    status: str,
    mode: str,
    suppressed_reason: Optional[str] = None,
) -> None:
    try:
        execute(
            get_db()
            .table("outbox")
            .insert(
                {
                    "to_phone": to_phone,
                    "text": text,
                    "status": status,
                    "mode": mode,
                    "suppressed_reason": suppressed_reason,
                }
            )
        )
    except Exception as exc:
        logger.error("Could not write outbox row for %s: %s", mask(to_phone), exc)
