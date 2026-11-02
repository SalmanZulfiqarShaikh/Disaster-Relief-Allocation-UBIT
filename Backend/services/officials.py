
from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional

from core import config
from core.phone import mask
from services import protocol
from services.whatsapp import send_message

logger = logging.getLogger("safezone.officials")

SERVICE_LABELS = {
    "fire": "Fire service",
    "medical": "Ambulance",
    "ngo": "Relief organisation",
}

SIMULATED_SUFFIX = "(simulated handoff — no live integration)"


def service_for(category: str) -> str:
    return protocol.node(category).get("emergency_kind", "ngo")


def requires_official(category: str) -> bool:
    return bool(protocol.node(category).get("official_first"))


def target_label(category: str, custom: Optional[str] = None) -> str:
    service = service_for(category)
    base = (custom or "").strip() or SERVICE_LABELS.get(service, "Emergency services")
    if not config.SHOW_SIMULATION_LABELS or SIMULATED_SUFFIX in base:
        return base[:120]
    return f"{base} {SIMULATED_SUFFIX}"[:120]


def handoff(category: str, custom_label: Optional[str] = None) -> Dict[str, Any]:
    service = service_for(category)
    number = config.get_emergency_number(category)

    if number is None:
        logger.warning(
            "No emergency number configured for %r; handoff for a %s case will "
            "show no call target.",
            service,
            category,
        )

    return {
        "service": service,
        "label": SERVICE_LABELS.get(service, "Emergency services"),
        "number": number,
        "number_is_simulated": bool(number) and config.EMERGENCY_NUMBERS_SIMULATED,
        "target_label": target_label(category, custom_label),
        "simulated": True,
        "required": requires_official(category),
        "note": (
            "SafeZone does not dispatch emergency services. The coordinator "
            "sends this link and, where a number is configured, calls it."
        ),
    }


def notify(
    record: Mapping[str, Any],
    *,
    case_id: int,
    url: str,
    category: str,
    area: Optional[str] = None,
    reason: Optional[str] = None,
    vuln_summary: Optional[str] = None,
) -> bool:
    if not config.OFFICIAL_HANDOFF_AUTOSEND:
        return False

    number = record.get("number")
    if not number:
        logger.warning(
            "Case %s: no official number configured, so no handoff was sent.", case_id
        )
        return False

    heading = f"SafeZone {record['label']} handoff"
    if config.SHOW_SIMULATION_LABELS:
        heading = f"{heading} {SIMULATED_SUFFIX}"

    lines = [
        heading,
        "",
        f"Case {case_id}: {(category or 'emergency').replace('_', ' ').capitalize()}"
        + (f" near {area}." if area else "."),
    ]
    if vuln_summary:
        lines.append(f"Who: {vuln_summary}.")
    if reason:
        lines.append(f"Why this ranks here: {reason}")
    lines.append("")
    lines.append(f"Full case: {url}")
    if config.SHOW_SIMULATION_LABELS:
        lines.append("")
        lines.append(
            "This is a prototype demonstration. SafeZone has no integration "
            "with any emergency service and has not dispatched anyone."
        )

    sent = send_message(number, "\n".join(lines))
    if sent:
        logger.info(
            "Case %s: %s handoff sent to %s", case_id, record["service"], mask(number)
        )
    else:
        logger.warning(
            "Case %s: %s handoff to %s was suppressed",
            case_id,
            record["service"],
            mask(number),
        )
    return sent
