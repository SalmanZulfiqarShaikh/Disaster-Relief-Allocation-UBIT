
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.geo import distance_km
from data import areas

OUT = Path(__file__).resolve().parent.parent / "data" / "localities.json"

ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)

BBOX = (24.70, 66.60, 25.20, 67.50)

PLACES = "suburb|neighbourhood|quarter|hamlet|village|town|city_block|residential"

QUERY = f"""
[out:json][timeout:180];
(
  node["place"~"^({PLACES})$"]["name"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["place"~"^({PLACES})$"]["name"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  relation["place"~"^({PLACES})$"]["name"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out center tags;
"""


def fetch() -> Dict[str, Any]:
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    last = ""
    for endpoint in ENDPOINTS:
        for attempt in (1, 2):
            try:
                print(f"  {endpoint} (attempt {attempt}) ...", flush=True)
                request = urllib.request.Request(
                    endpoint,
                    data=body,
                    headers={"User-Agent": "SafeZone/1.0 (student project)"},
                )
                with urllib.request.urlopen(request, timeout=240) as response:
                    return json.loads(response.read().decode())
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last = f"{endpoint}: {exc}"
                print(f"    failed: {exc}", flush=True)
                time.sleep(5)
    raise SystemExit(f"Every Overpass mirror failed. Last error -- {last}")


def normalise(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum() or ch == " ").strip()


def main() -> None:
    print("Fetching named places in Karachi from OpenStreetMap ...")
    payload = fetch()
    elements = payload.get("elements", [])
    print(f"  {len(elements)} raw elements")

    centres: List[Tuple[str, float, float]] = []
    for area in areas.AREAS:
        centres.append((area["id"], float(area["lat"]), float(area["lng"])))

    taken = {normalise(text) for text, _ in areas.search_index()}

    rows: Dict[str, Dict[str, Any]] = {}
    skipped_outside = skipped_dupe = skipped_short = 0

    for element in elements:
        tags = element.get("tags") or {}
        name = (tags.get("name:en") or tags.get("name") or "").strip()
        if not name:
            continue

        point = element.get("center") or element
        lat, lng = point.get("lat"), point.get("lon")
        if lat is None or lng is None:
            continue
        lat, lng = float(lat), float(lng)

        if not (BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lng <= BBOX[3]):
            skipped_outside += 1
            continue

        key = normalise(name)
        if len(key) < 4:
            skipped_short += 1
            continue
        if key in taken:
            skipped_dupe += 1
            continue
        if key in rows:
            continue

        nearest_id, nearest_km = min(
            ((aid, distance_km(lat, lng, alat, alng)) for aid, alat, alng in centres),
            key=lambda pair: pair[1],
        )

        rows[key] = {
            "name": name,
            "lat": round(lat, 5),
            "lng": round(lng, 5),
            "area": nearest_id,
            "km": round(nearest_km, 2),
            "place": tags.get("place", ""),
        }

    out = {
        "source": "OpenStreetMap contributors, ODbL",
        "built_from": "Overpass API",
        "count": len(rows),
        "localities": dict(sorted(rows.items())),
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote {OUT}")
    print(f"  {len(rows)} localities")
    print(f"  skipped: {skipped_dupe} already matchable, {skipped_outside} outside Karachi, {skipped_short} too short")

    far = [r for r in rows.values() if r["km"] > 8]
    if far:
        print(f"\n  {len(far)} sit more than 8 km from their assigned area centre.")
        print("  Worth a glance -- these are the likeliest mis-assignments:")
        for row in sorted(far, key=lambda r: -r["km"])[:15]:
            print(f"    {row['name']:34} -> {row['area']:20} {row['km']:5.1f} km")


if __name__ == "__main__":
    main()
