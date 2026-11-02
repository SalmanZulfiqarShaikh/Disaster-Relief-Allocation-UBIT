
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from core import config
from core.config import get_emergency_number

logger = logging.getLogger("safezone.protocol")

GRAPH_PATH = Path(__file__).parent.parent / "data" / "protocol_graph.json"
DEFAULT_CATEGORY = "other"


@lru_cache(maxsize=1)
def _graph() -> dict[str, Any]:
    with GRAPH_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def categories() -> list[str]:
    return list(_graph()["categories"].keys())


def node(category: str) -> dict[str, Any]:
    cats = _graph()["categories"]
    key = (category or "").strip().lower()
    if key not in cats:
        if key:
            logger.warning("Unknown category %r; using %r", key, DEFAULT_CATEGORY)
        key = DEFAULT_CATEGORY
    return {"id": key, **cats[key]}


def safety_steps(category: str) -> list[str]:
    return node(category)["safety_steps"]


def next_question(category: str, asked: int = 0) -> Optional[str]:
    questions = node(category)["questions"]
    return questions[asked] if asked < min(len(questions), 2) else None


def is_volunteer_eligible(category: str) -> bool:
    return bool(node(category)["volunteer_eligible"])


def guidance_reply(category: str, shelter: Optional[str] = None) -> tuple[str, list[str]]:
    n = node(category)
    path = [f"category:{n['id']}"]
    lines: list[str] = []

    number = get_emergency_number(n["emergency_kind"])
    if number:
        label = {
            "fire": "Fire service",
            "medical": "Ambulance",
            "ngo": "Relief organisation",
        }.get(n["emergency_kind"], "Emergency services")
        note = config.emergency_number_note()
        if note:
            path.append("simulated_emergency_number")
        if n["official_first"]:
            lines.append(f"Call {label} now: {number}{note}")
            path.append("official_first")
        else:
            lines.append(f"{label}: {number}{note}")
        lines.append("")
    else:
        path.append("emergency_number_missing")

    for step in n["safety_steps"]:
        lines.append(f"- {step}")
    path.append("safety_steps")

    if shelter:
        lines.append("")
        lines.append(f"If you can move safely, the nearest shelter is {shelter}.")
        path.append("shelter")

    lines.append("")
    lines.append("We have flagged your case and alerted help nearby.")
    lines.append("Send your location pin or tell me your area, and reply here with updates.")

    return "\n".join(lines), path