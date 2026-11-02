
from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("safezone.config")


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _get_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


SQLSERVER_CONNECTION_STRING: str = os.getenv("SQLSERVER_CONNECTION_STRING", "").strip()

MOCK_MODE: bool = _get_bool("MOCK_MODE", True)

DEMO_MODE: bool = _get_bool("DEMO_MODE", True)

ALLOWLIST_ONLY: bool = _get_bool("ALLOWLIST_ONLY", True)

KILL_SWITCH: bool = _get_bool("KILL_SWITCH", False)

GREETING_REPLY: bool = _get_bool("GREETING_REPLY", True)

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").strip().upper()

ZONE_ALERTS_ENABLED: bool = _get_bool("ZONE_ALERTS_ENABLED", True)
ZONE_ALERT_MIN_URGENCY: float = float(os.getenv("ZONE_ALERT_MIN_URGENCY", "0.75"))
ZONE_ALERT_MIN_REPORTS: int = _get_int("ZONE_ALERT_MIN_REPORTS", 3)
ZONE_ALERT_MAX_RECIPIENTS: int = _get_int("ZONE_ALERT_MAX_RECIPIENTS", 50)

REGISTRATION_CODE_TTL_MINUTES: int = _get_int("REGISTRATION_CODE_TTL_MINUTES", 30)

WHATSAPP_PUBLIC_NUMBER: str = os.getenv("WHATSAPP_PUBLIC_NUMBER", "").strip().lstrip("+")

VOLUNTEER_OFFER_RING_SIZE: int = _get_int("VOLUNTEER_OFFER_RING_SIZE", 3)
VOLUNTEER_ACCEPT_TIMEOUT_S: int = _get_int("VOLUNTEER_ACCEPT_TIMEOUT_S", 300)
VOLUNTEER_ARRIVE_TIMEOUT_S: int = _get_int("VOLUNTEER_ARRIVE_TIMEOUT_S", 900)
PERSON_SILENCE_TIMEOUT_S: int = _get_int("PERSON_SILENCE_TIMEOUT_S", 900)
GLOBAL_MESSAGE_CAP: int = _get_int("GLOBAL_MESSAGE_CAP", 500)
def _origin(raw: str) -> str:
    value = (raw or "").strip().rstrip("/")
    for suffix in ("/webhook/whatsapp", "/webhook", "/api"):
        if value.endswith(suffix):
            value = value[: -len(suffix)].rstrip("/")
    return value


PUBLIC_BASE_URL: str = _origin(os.getenv("PUBLIC_BASE_URL", ""))
RESPONDER_LINK_TTL_HOURS: int = _get_int("RESPONDER_LINK_TTL_HOURS", 24)

VOLUNTEER_MAX_CASES: int = max(1, _get_int("VOLUNTEER_MAX_CASES", 1))

ADMIN_EMAIL: str = (
    os.getenv("ADMIN_EMAILS", "") or os.getenv("ADMIN_EMAIL", "")
).strip()


def admin_emails() -> tuple:
    return tuple(
        part.strip().lower() for part in ADMIN_EMAIL.split(",") if part.strip()
    )
ADMIN_PASSWORD_HASH: str = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
SESSION_SECRET: str = os.getenv("SESSION_SECRET", "").strip()
SESSION_TTL_HOURS: int = _get_int("SESSION_TTL_HOURS", 12)

PER_NUMBER_RATE_LIMIT: int = _get_int("PER_NUMBER_RATE_LIMIT", 10)
PER_NUMBER_RATE_WINDOW_S: int = _get_int("PER_NUMBER_RATE_WINDOW_S", 300)

_raw_allowlist = os.getenv("DEMO_ALLOWLIST", "").strip()
DEMO_ALLOWLIST: List[str] = [
    num.strip() for num in _raw_allowlist.split(",") if num.strip()
]

_raw_demo_volunteers = os.getenv("DEMO_VOLUNTEERS", "").strip()
DEMO_VOLUNTEERS: List[Dict] = []
if _raw_demo_volunteers:
    try:
        DEMO_VOLUNTEERS = json.loads(_raw_demo_volunteers)
    except Exception:
        logger.error("DEMO_VOLUNTEERS is not valid JSON; ignoring it.")

EMERGENCY_FIRE: str = os.getenv("EMERGENCY_FIRE", "").strip()
EMERGENCY_AMBULANCE: str = os.getenv("EMERGENCY_AMBULANCE", "").strip()
EMERGENCY_NGO: str = os.getenv("EMERGENCY_NGO", "").strip()

SHOW_SIMULATION_LABELS: bool = _get_bool("SHOW_SIMULATION_LABELS", False)

EMERGENCY_NUMBERS_SIMULATED: bool = _get_bool(
    "EMERGENCY_NUMBERS_SIMULATED", SHOW_SIMULATION_LABELS
)

OFFICIAL_HANDOFF_AUTOSEND: bool = _get_bool("OFFICIAL_HANDOFF_AUTOSEND", True)

_raw_coordinators = os.getenv("COORDINATOR_NUMBERS", "").strip()
COORDINATOR_NUMBERS: List[str] = [
    number.strip() for number in _raw_coordinators.split(",") if number.strip()
]
COORDINATOR_NOTIFY: bool = _get_bool("COORDINATOR_NOTIFY", True)

COORDINATOR_DEFAULT_CHANNEL: str = os.getenv(
    "COORDINATOR_DEFAULT_CHANNEL", "responder"
).strip().lower()

SIMULATED_NUMBER_NOTE = "(demo number, not the real emergency service)"


def emergency_number_note() -> str:
    return f" {SIMULATED_NUMBER_NOTE}" if EMERGENCY_NUMBERS_SIMULATED else ""


def get_emergency_number(category: str) -> Optional[str]:
    cat = (category or "").strip().lower()

    if cat in ("fire", "structural"):
        number, setting = EMERGENCY_FIRE, "EMERGENCY_FIRE"
    elif cat in ("medical", "trapped", "flood"):
        number, setting = EMERGENCY_AMBULANCE, "EMERGENCY_AMBULANCE"
    else:
        number, setting = EMERGENCY_NGO, "EMERGENCY_NGO"

    if not number:
        logger.error(
            "%s is not configured; %s guidance will omit the official number.",
            setting,
            cat or "unknown",
        )
        return None

    return number


WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "").strip()
WHATSAPP_PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID", "").strip()
WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()
WHATSAPP_APP_SECRET: str = os.getenv("WHATSAPP_APP_SECRET", "").strip()

LLM_API_KEY: str = os.getenv("LLM_API_KEY", "").strip()
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "deepseek").strip().lower()
LLM_MODEL: str = os.getenv("LLM_MODEL", "").strip()

DEFAULT_LLM_PROVIDERS = ("deepseek", "groq", "gemini")

_raw_providers = os.getenv("LLM_PROVIDERS", "").strip()
LLM_PROVIDERS: List[str] = [
    name.strip().lower() for name in _raw_providers.split(",") if name.strip()
] or list(DEFAULT_LLM_PROVIDERS)

DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "").strip()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "").strip()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "").strip()

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "").strip()

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "").strip()


def startup_report() -> List[str]:
    problems: List[str] = []

    if not EMERGENCY_FIRE:
        problems.append("EMERGENCY_FIRE is not set — fire guidance will omit the official number.")
    if not EMERGENCY_AMBULANCE:
        problems.append(
            "EMERGENCY_AMBULANCE is not set — medical, trapped and flood guidance "
            "will omit the official number."
        )
    if not EMERGENCY_NGO:
        problems.append(
            "EMERGENCY_NGO is not set — food, water and unclassified guidance "
            "will omit the relief contact."
        )

    if not ALLOWLIST_ONLY and not SHOW_SIMULATION_LABELS and (
        EMERGENCY_FIRE or EMERGENCY_AMBULANCE or EMERGENCY_NGO
    ):
        problems.append(
            "ALLOWLIST_ONLY is off and SHOW_SIMULATION_LABELS is off — anyone "
            "who messages this number will be told to call the configured "
            "emergency numbers with no caveat. Make sure those are the real "
            "official numbers."
        )

    if KILL_SWITCH:
        problems.append("KILL_SWITCH is on — every outbound message will be suppressed.")

    if not MOCK_MODE and not WHATSAPP_TOKEN:
        problems.append("MOCK_MODE is off but WHATSAPP_TOKEN is empty — WhatsApp sends will fail.")

    if not MOCK_MODE and not WHATSAPP_APP_SECRET:
        problems.append(
            "MOCK_MODE is off but WHATSAPP_APP_SECRET is empty — webhook signatures "
            "will not be verified."
        )

    if COORDINATOR_NOTIFY and not COORDINATOR_NUMBERS:
        problems.append(
            "COORDINATOR_NUMBERS is empty — nobody will be told when a case "
            "needs approval, so cases will sit in the queue unseen."
        )

    if ALLOWLIST_ONLY and not DEMO_ALLOWLIST:
        problems.append(
            "ALLOWLIST_ONLY is on but DEMO_ALLOWLIST is empty — every outbound "
            "message will be suppressed."
        )

    if not SQLSERVER_CONNECTION_STRING:
        problems.append(
            "SQLSERVER_CONNECTION_STRING is missing — database access "
            "will raise DbError."
        )

    return problems
