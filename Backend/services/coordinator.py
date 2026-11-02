
from __future__ import annotations

import logging
from typing import Any, List, Mapping, Optional

from core import config
from core.phone import mask, try_normalize
from services.whatsapp import send_message

logger = logging.getLogger("safezone.coordinator")


def numbers() -> List[str]:
    seen: List[str] = []
    for raw in config.COORDINATOR_NUMBERS:
        normalized = try_normalize(raw)
        if normalized and normalized not in seen:
            seen.append(normalized)
        elif not normalized:
            logger.warning("Ignoring unusable coordinator number %r", mask(str(raw)))
    return seen


def notify_new_case(
    *,
    case_id: Any,
    category: str,
    priority_score: Any,
    reason: Optional[str] = None,
    vuln_summary: Optional[str] = None,
    area: Optional[str] = None,
    location_known: bool = False,
    report_count: Any = 1,
) -> int:
    if not config.COORDINATOR_NOTIFY:
        return 0

    recipients = numbers()
    if not recipients:
        logger.warning(
            "Case %s is waiting for approval but COORDINATOR_NUMBERS is empty, "
            "so nobody was told.",
            case_id,
        )
        return 0

    text = compose(
        case_id=case_id,
        category=category,
        priority_score=priority_score,
        reason=reason,
        vuln_summary=vuln_summary,
        area=area,
        location_known=location_known,
        report_count=report_count,
    )

    sent = 0
    for number in recipients:
        try:
            if send_message(number, text):
                sent += 1
            else:
                logger.info("Coordinator alert to %s was suppressed", mask(number))
        except Exception:
            logger.exception("Could not alert coordinator %s", mask(number))

    logger.info("Case %s: alerted %d of %d coordinators", case_id, sent, len(recipients))
    return sent


def compose(
    *,
    case_id: Any,
    category: str,
    priority_score: Any,
    reason: Optional[str] = None,
    vuln_summary: Optional[str] = None,
    area: Optional[str] = None,
    location_known: bool = False,
    report_count: Any = 1,
) -> str:
    label = (category or "emergency").replace("_", " ").capitalize()
    where = f" near {area}" if area else ""

    lines = [f"SafeZone: case {case_id} needs a handoff decision", "", f"{label}{where}."]

    if vuln_summary:
        lines.append(f"Who: {vuln_summary}.")

    try:
        count = int(report_count or 1)
    except (TypeError, ValueError):
        count = 1
    if count > 1:
        lines.append(f"{count} separate reports.")

    if not location_known:
        lines.append("No exact location shared yet — may need a phone call.")

    if reason:
        lines.append(f"Why it ranks here: {reason}")

    try:
        lines.append(f"Priority {float(priority_score):.2f}")
    except (TypeError, ValueError):
        pass

    lines.append("")
    lines.append("Nearby volunteers have already been offered this.")
    lines.append(f"Reply APPROVE {case_id} to send it to the official service, or REJECT {case_id}.")
    if config.PUBLIC_BASE_URL:
        lines.append(f"Control room: {config.PUBLIC_BASE_URL}/control")

    return "\n".join(lines)
