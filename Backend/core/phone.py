
import re
from typing import Optional


class PhoneError(ValueError):
    pass


def normalize_phone(raw: str) -> str:
    if not raw or not isinstance(raw, str):
        raise PhoneError("Phone number must be a non-empty string")

    cleaned = re.sub(r"[\s\-\(\)\+]", "", raw.strip())

    if not cleaned.isdigit():
        raise PhoneError(f"Phone number contains invalid non-numeric characters: '{raw}'")

    if cleaned.startswith("03") and len(cleaned) == 11:
        return "92" + cleaned[1:]

    if cleaned.startswith("923") and len(cleaned) == 12:
        return cleaned

    if cleaned.startswith("00923") and len(cleaned) == 14:
        return cleaned[2:]

    if cleaned.startswith("3") and len(cleaned) == 10:
        return "92" + cleaned

    raise PhoneError(f"Cannot confidently normalize phone number: '{raw}' (cleaned: '{cleaned}')")


def try_normalize(raw: str) -> Optional[str]:
    try:
        return normalize_phone(raw)
    except PhoneError:
        return None


def mask(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit()) if isinstance(phone, str) else ""
    if not digits:
        return "****"
    visible = digits[-4:]
    return "*" * (len(digits) - len(visible)) + visible


def format_display(phone: str) -> str:
    normalized = try_normalize(phone)
    if normalized and normalized.startswith("92") and len(normalized) == 12:
        return f"+{normalized[:2]} {normalized[2:5]} {normalized[5:]}"
    return str(phone).strip() if phone is not None else ""
