
from __future__ import annotations

import difflib
import logging
import re
from typing import Any, Dict, Mapping, Optional

from core import config
from data import areas
from services import llm, protocol

logger = logging.getLogger("safezone.extract")

CATEGORIES = ("flood", "fire", "medical", "trapped", "structural", "other")
URGENCIES = ("low", "medium", "high", "critical")

SYSTEM_PROMPT = (
    "You extract structured emergency reports for a Karachi emergency-response "
    "system. Reply with a single JSON object and nothing else. Use null for any "
    "field the person did not state; never guess vulnerability. Vulnerability "
    "describes ANYONE at the scene, not only the sender: 'my elderly mother is "
    "with me' means elderly is true, 'I am here with my kids' means "
    "children_present is true. State a field only when the person actually "
    "said it, and use null -- never false -- when they did not. Categories: "
    "flood, fire, medical, trapped, structural, other. Urgency: low, medium, "
    "high, critical. Location is not known until an exact pin or address is "
    "given; a neighbourhood name alone is a zone_guess, not an exact location."
    "\n\n"
    "The category decides which emergency service this case is handed to, so "
    "when a report describes more than one thing, pick the one that needs the "
    "most urgent service, in this order: fire, then medical, then structural, "
    "then trapped, then flood. 'Water came into my house and my father is "
    "unconscious' is medical, not flood -- the water is the context, the "
    "unconscious man is the emergency. 'Our street is flooded' with nobody "
    "hurt is flood. Put the parts you did not choose in needs, so the "
    "coordinator still sees them."
    "\n\n"
    "For zone_guess, return EXACTLY one id from the list below, or null if the "
    "person named no area you recognise. People write their own neighbourhood "
    "in many ways and often misspell it -- 'Gulistan-e-Jauhar', 'Gulistan e "
    "Johar', 'Jauhar', 'Guilstan' and 'johar town' all mean the id johar. Map "
    "landmarks, roads, chowrangis and markets onto the area that contains "
    "them. Never invent an id that is not on this list.\n\n"
    "Areas (id, then the common name):\n" + areas.prompt_list()
)

AREA_MATCH_CUTOFF = 0.75

CATEGORY_PATTERNS = (
    (
        "fire",
        re.compile(
            r"\b(fire|smoke|burning|flames|blaze|aag|dhuan|dhuaan|jal rah[ai])\b",
            re.I,
        ),
    ),
    (
        "medical",
        re.compile(
            r"\b(medical|heart attack|cardiac|stroke|unconscious|behosh|bleeding|"
            r"injured|injury|zakhmi|breathing|saans nahi|asthma|diabetic|pregnant|"
            r"labour|labor)\b",
            re.I,
        ),
    ),
    (
        "structural",
        re.compile(
            r"\b(collapse|collapsed|building damage|cracked|wall fell|roof fell|"
            r"chat gir|deewar gir|gir gayi)\b",
            re.I,
        ),
    ),
    (
        "trapped",
        re.compile(
            r"\b(trapped|stuck|stranded|can'?t get out|cannot get out|phans)",
            re.I,
        ),
    ),
    (
        "flood",
        re.compile(
            r"\b(flood|flooded|flooding|water (is )?(rising|filled)|water has filled|"
            r"rain water|sewer|paani|pani|barish|barsaat)\b",
            re.I,
        ),
    ),
)

CRITICAL_PATTERNS = re.compile(
    r"\b(not breathing|can'?t breathe|cannot breathe|unconscious|behosh|"
    r"saans nahi|dying|cardiac arrest|no pulse|severe bleeding)\b",
    re.I,
)
HIGH_PATTERNS = re.compile(
    r"\b(urgent|trapped|stuck|phans|bleeding|injured|zakhmi|baby|infant|child|"
    r"children|bachay|elderly|disabled|wheelchair|pregnant|"
    r"water (is )?rising|serious)\b",
    re.I,
)
LOW_PATTERNS = re.compile(r"\b(safe|no one hurt|nobody hurt|minor|not urgent)\b", re.I)

VULNERABILITY_PATTERNS = {
    "elderly": re.compile(r"\b(elderly|old man|old woman|grandfather|grandmother|senior)\b", re.I),
    "alone": re.compile(r"\b(alone|by myself|on my own|no one with me)\b", re.I),
    "mobility_limited": re.compile(
        r"\b(disabled|wheelchair|can'?t walk|cannot walk|bedridden|broken leg)\b", re.I
    ),
    "children_present": re.compile(r"\b(children|child|kids|baby|infant|toddler)\b", re.I),
    "chronic_illness": re.compile(
        r"\b(diabetes|diabetic|asthma|heart condition|blood pressure|kidney|"
        r"chronic|cancer)\b",
        re.I,
    ),
}

FLOOR_PATTERN = re.compile(
    r"\b(ground|first|second|third|fourth|fifth|basement)\s+floor\b", re.I
)
PEOPLE_PATTERN = re.compile(
    r"\b(\d{1,3})\s*(?:people|persons|of us|family members|kids|children)\b", re.I
)
COORDINATES_PATTERN = re.compile(r"(-?\d{1,3}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})")
LANDMARK_PATTERN = re.compile(
    r"\b(?:near|behind|opposite|next to|in front of)\s+([^.,;\n]{2,60})", re.I
)

_AREA_INDEX = sorted(areas.search_index(), key=lambda pair: -len(pair[0]))

NEEDS_PATTERNS = {
    "evacuation": re.compile(r"\b(evacuate|evacuation|get out|roof|stranded)\b", re.I),
    "rescue": re.compile(r"\b(rescue|trapped|stuck)\b", re.I),
    "medical": re.compile(r"\b(medical|medicine|doctor|ambulance|injured|bleeding)\b", re.I),
    "water": re.compile(r"\b(drinking water|thirsty|water supply)\b", re.I),
    "shelter": re.compile(r"\b(shelter|homeless|no roof|house gone)\b", re.I),
}


def quick_category(text: str) -> str:
    body = text or ""
    for name, pattern in CATEGORY_PATTERNS:
        if pattern.search(body):
            return name
    return "other"


def extract_report(text: str) -> Dict[str, Any]:
    body = (text or "").strip()
    if not body:
        return _keyword_extract("")

    if config.MOCK_MODE:
        return _keyword_extract(body)

    try:
        return _llm_extract(body)
    except Exception as exc:
        logger.warning("LLM extraction failed (%s); falling back to keywords", exc)
        return _keyword_extract(body)


def _keyword_extract(text: str) -> Dict[str, Any]:
    category = quick_category(text)
    location_text, location_known = _location(text)
    missing_fields = [] if location_known else ["exact_location"]

    return {
        "category": category,
        "category_confidence": 0.85 if category != "other" else 0.4,
        "urgency": _urgency(text),
        "people_count": _people_count(text),
        "location_text": location_text,
        "zone_guess": _zone(text),
        "vulnerability": _vulnerability(text),
        "needs": [name for name, pattern in NEEDS_PATTERNS.items() if pattern.search(text)],
        "missing_fields": missing_fields,
        "next_question": protocol.next_question(category, asked=0 if not location_known else 1),
    }


def _urgency(text: str) -> str:
    if CRITICAL_PATTERNS.search(text):
        return "critical"
    if LOW_PATTERNS.search(text) and not HIGH_PATTERNS.search(text):
        return "low"
    if HIGH_PATTERNS.search(text):
        return "high"
    return "medium"


def _people_count(text: str) -> Optional[int]:
    match = PEOPLE_PATTERN.search(text)
    if not match:
        return None
    try:
        count = int(match.group(1))
    except ValueError:
        return None
    return count if 1 <= count <= 999 else None


def _vulnerability(text: str) -> Dict[str, Any]:
    vulnerability: Dict[str, Any] = {
        "elderly": None,
        "alone": None,
        "mobility_limited": None,
        "children_present": None,
        "chronic_illness": None,
        "floor": None,
    }
    for field, pattern in VULNERABILITY_PATTERNS.items():
        if pattern.search(text):
            vulnerability[field] = True

    floor = FLOOR_PATTERN.search(text)
    if floor:
        vulnerability["floor"] = floor.group(1).lower()

    return vulnerability


def _location(text: str) -> tuple[Optional[str], bool]:
    coordinates = COORDINATES_PATTERN.search(text)
    if coordinates:
        return f"{coordinates.group(1)},{coordinates.group(2)}", True

    landmark = LANDMARK_PATTERN.search(text)
    if landmark:
        return landmark.group(0).strip(), False

    zone = _zone(text)
    if zone:
        return zone, False

    return None, False


def resolve_area(value: Any) -> Optional[str]:
    if not value:
        return None

    candidate = re.sub(r"[^\w\s-]", " ", str(value).strip().lower())
    candidate = " ".join(candidate.replace("-", " ").split())
    if not candidate:
        return None

    for phrase, area_id in _AREA_INDEX:
        if candidate == phrase.replace("-", " "):
            return area_id

    phrases = [phrase.replace("-", " ") for phrase, _ in _AREA_INDEX]
    close = difflib.get_close_matches(candidate, phrases, n=1, cutoff=AREA_MATCH_CUTOFF)
    if close:
        index = phrases.index(close[0])
        return _AREA_INDEX[index][1]

    return None


def _zone(text: str) -> Optional[str]:
    flattened = re.sub(r"[^\w\s]", " ", (text or "").lower().replace("-", " "))
    haystack = " " + " ".join(flattened.split()) + " "
    for phrase, area_id in _AREA_INDEX:
        needle = " " + phrase.replace("-", " ") + " "
        if needle in haystack:
            return area_id

    locality = areas.find_locality(text)
    return locality["area"] if locality else None


USER_PROMPT_TEMPLATE = (
    "Extract this WhatsApp emergency report. Return JSON with keys "
    "category, category_confidence, urgency, people_count, "
    "location_text, zone_guess, vulnerability (elderly, alone, "
    "mobility_limited, children_present, chronic_illness, floor), "
    "needs, missing_fields, next_question.\n\nReport: {text}"
)


def _llm_extract(text: str) -> Dict[str, Any]:
    data = llm.complete_json(
        SYSTEM_PROMPT,
        USER_PROMPT_TEMPLATE.format(text=text),
    )
    return _normalise(data, text)


def _normalise(data: Mapping[str, Any], text: str = "") -> Dict[str, Any]:
    category = str(data.get("category") or "other").strip().lower()
    if category not in CATEGORIES:
        category = "other"

    urgency = str(data.get("urgency") or "medium").strip().lower()
    if urgency not in URGENCIES:
        urgency = "medium"

    vulnerability = data.get("vulnerability")
    if not isinstance(vulnerability, Mapping):
        vulnerability = {}
    normalised_vuln = {
        field: _optional_bool(vulnerability.get(field))
        for field in (
            "elderly",
            "alone",
            "mobility_limited",
            "children_present",
            "chronic_illness",
        )
    }
    floor = vulnerability.get("floor")
    normalised_vuln["floor"] = str(floor).strip().lower() if floor else None

    location_text = data.get("location_text")
    location_text = str(location_text).strip() if location_text else None

    missing = data.get("missing_fields")
    missing_fields = [str(item) for item in missing] if isinstance(missing, list) else []
    if not missing_fields:
        missing_fields = [] if location_text else ["exact_location"]

    next_question = data.get("next_question")
    if not next_question:
        next_question = protocol.next_question(
            category, asked=0 if "exact_location" in missing_fields else 1
        )

    confidence = data.get("category_confidence")
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5

    people_count = data.get("people_count")
    try:
        people_count = int(people_count) if people_count is not None else None
    except (TypeError, ValueError):
        people_count = None

    needs = data.get("needs")
    needs = [str(item) for item in needs] if isinstance(needs, list) else []

    return {
        "category": category,
        "category_confidence": round(confidence, 2),
        "urgency": urgency,
        "people_count": people_count,
        "location_text": location_text,
        "zone_guess": resolve_area(data.get("zone_guess")) or _zone(text),
        "vulnerability": normalised_vuln,
        "needs": needs,
        "missing_fields": missing_fields,
        "next_question": next_question,
    }


def _optional_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return None
