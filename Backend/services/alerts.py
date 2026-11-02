
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from core import config
from core.db import execute, get_db
from core.phone import mask
from services import protocol, risk
from services.whatsapp import send_message

logger = logging.getLogger("safezone.alerts")


def alert_for_incident(
    incident: Mapping[str, Any],
    *,
    exclude_person_id: Any = None,
    now: Optional[datetime] = None,
) -> List[int]:
    if not config.ZONE_ALERTS_ENABLED:
        return []

    zone_id = (incident.get("zone_id") or "").strip().lower()
    if not zone_id:
        return []

    if not _is_serious_enough(incident):
        return []

    incident_id = incident.get("id")
    category = incident.get("category") or "other"
    already = _already_alerted(incident_id)

    recipients = []
    for person in _select("people", zone_id=zone_id):
        person_id = person.get("id")
        if person_id is None or person_id == exclude_person_id:
            continue
        if not person.get("is_registered") or not person.get("wants_alerts"):
            continue
        if person_id in already:
            continue
        if not person.get("phone"):
            continue
        recipients.append(person)

    if not recipients:
        return []

    capped = recipients[: max(config.ZONE_ALERT_MAX_RECIPIENTS, 0)]
    if len(capped) < len(recipients):
        logger.warning(
            "Zone %s has %d alertable people; capping at %d for incident %s",
            zone_id,
            len(recipients),
            len(capped),
            incident_id,
        )

    text = compose(category, zone_id)
    moment = now or datetime.now(timezone.utc)
    alerted: List[int] = []

    for person in capped:
        _insert(
            "zone_alerts",
            {
                "incident_id": incident_id,
                "person_id": person["id"],
                "zone_id": zone_id,
                "sent_at": moment.isoformat(),
            },
        )
        if send_message(person["phone"], text):
            alerted.append(person["id"])
        else:
            logger.info("Zone alert to %s was suppressed", mask(person["phone"]))

    logger.info(
        "Zone alert for incident %s reached %d of %d in %s",
        incident_id,
        len(alerted),
        len(capped),
        zone_id,
    )
    return alerted


def compose(category: str, zone_id: str) -> str:
    area = zone_id.replace("-", " ").title()
    label = (category or "emergency").replace("_", " ")

    lines = [f"SafeZone alert: a {label} has been reported in {area}."]

    number = config.get_emergency_number(category)
    if number:
        service = protocol.node(category).get("emergency_kind", "ngo")
        service_label = {
            "fire": "Fire service",
            "medical": "Ambulance",
            "ngo": "Relief organisation",
        }.get(
            service, "Emergency services"
        )
        lines.append(f"{service_label}: {number}{config.emergency_number_note()}")

    lines.append("")
    for step in protocol.safety_steps(category):
        lines.append(f"- {step}")

    lines.append("")
    lines.append("If you need help, reply here with what is happening and where you are.")
    lines.append("Reply STOP to turn off these alerts.")
    return "\n".join(lines)


def _is_serious_enough(incident: Mapping[str, Any]) -> bool:
    urgency = risk.urgency_score(incident.get("urgency"))
    if urgency >= config.ZONE_ALERT_MIN_URGENCY:
        return True

    try:
        report_count = int(incident.get("report_count") or 1)
    except (TypeError, ValueError):
        report_count = 1
    return report_count >= config.ZONE_ALERT_MIN_REPORTS


def _already_alerted(incident_id: Any) -> set:
    if incident_id is None:
        return set()
    return {
        row.get("person_id")
        for row in _select("zone_alerts", incident_id=incident_id)
        if row.get("person_id") is not None
    }


def _select(table: str, **filters: Any) -> List[Dict[str, Any]]:
    query = get_db().table(table).select("*")
    for column, value in filters.items():
        query = query.eq(column, value)
    rows = list(getattr(execute(query), "data", None) or [])
    return [row for row in rows if isinstance(row, Mapping)]


def _insert(table: str, row: Mapping[str, Any]) -> Any:
    try:
        return execute(get_db().table(table).insert(dict(row)))
    except Exception as exc:
        logger.error("Could not record zone alert: %s", exc)
        return None
