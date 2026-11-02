
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, List, Tuple

logger = logging.getLogger("safezone.reset")

TABLES: Tuple[Tuple[str, str], ...] = (
    ("dispatches", "id"),
    ("responder_links", "token"),
    ("zone_alerts", "id"),
    ("events", "id"),
    ("reports", "id"),
    ("cases", "id"),
    ("incidents", "id"),
    ("registrations", "code"),
    ("outbox", "id"),
    ("people", "id"),
    ("volunteers", "id"),
    ("zones", "id"),
)


def clear(client, table: str, key: str) -> int:
    from core.db import execute

    try:
        before = execute(client.table(table).select(key))
        count = len(list(getattr(before, "data", None) or []))
    except Exception as exc:
        logger.warning("Could not read %s: %s", table, exc)
        return 0

    if count == 0:
        return 0

    try:
        execute(client.table(table).delete().not_.is_(key, "null"))
    except Exception as exc:
        logger.error("Could not clear %s: %s", table, exc)
        return 0

    return count


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wipe demo data and re-seed.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required. Confirms you mean to delete every row.",
    )
    parser.add_argument(
        "--keep-volunteers",
        action="store_true",
        help="Leave volunteers and their ON DUTY status alone.",
    )
    parser.add_argument(
        "--no-samples",
        action="store_true",
        help="Re-seed zones and volunteers but leave the case queue empty.",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Clear without re-seeding zones and volunteers.",
    )
    parser.add_argument(
        "--off-duty",
        action="store_true",
        help=(
            "Leave demo volunteers off duty. Without this, demo mode puts them "
            "on duty so a rehearsal does not need ON DUTY from every handset."
        ),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

    from core import config
    from core.db import get_db

    if not args.yes:
        print("This deletes EVERY row in:")
        print("  " + ", ".join(table for table, _key in TABLES))
        print("\nTarget: SQL Server (SQLSERVER_CONNECTION_STRING)")
        print("\nRe-run with --yes if that is what you want.")
        return 1

    client = get_db()
    print("Clearing SQL Server database\n")

    tables = TABLES
    if args.keep_volunteers:
        tables = tuple((t, k) for t, k in TABLES if t != "volunteers")
        print("Keeping volunteers and their duty status.\n")

    total = 0
    for table, key in tables:
        removed = clear(client, table, key)
        total += removed
        print(f"  {table:<18} {removed:>6} rows")

    print(f"\n{total} rows deleted.")

    if args.no_seed:
        print("Skipped re-seeding (--no-seed).")
        return 0

    from core.phone import mask
    from data import seed as seed_module

    print("\nRe-seeding...")
    counts = seed_module.seed(client, samples=not args.no_samples)
    print(
        f"  {counts['zones']} zones, {counts['volunteers']} volunteers, "
        f"{counts['incidents']} sample incidents"
    )
    for volunteer in seed_module.volunteer_plan():
        marker = "  (PLACEHOLDER — set DEMO_VOLUNTEERS)" if volunteer["is_placeholder"] else ""
        print(
            f"  group {volunteer['group']}: {mask(volunteer['phone'])} "
            f"covers {len(volunteer['zone_ids'])} areas{marker}"
        )

    if config.DEMO_MODE and not args.off_duty:
        from core.db import execute

        updated = execute(
            client.table("volunteers")
            .update({"status": "on_duty"})
            .eq("is_demo", True)
        )
        rows = getattr(updated, "data", None) or []
        print(f"\n{len(rows)} demo volunteers set ON DUTY.")
        print(
            "This is the database row only. It does NOT reopen the 24-hour\n"
            "WhatsApp window -- each handset must still message SafeZone, or\n"
            "its offers will be suppressed without an error."
        )
    elif args.keep_volunteers:
        print("\nExisting volunteers kept their duty status. Check with GET /api/volunteers.")
    else:
        print("\nVolunteers are seeded OFF DUTY. Each phone must send ON DUTY.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
