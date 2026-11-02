

export const BOUNDS = {
  west: 66.94,
  east: 67.24,
  south: 24.76,
  north: 25.06,
} as const;

const SPAN_LNG = BOUNDS.east - BOUNDS.west;
const SPAN_LAT = BOUNDS.north - BOUNDS.south;

const clamp = (value: number) => Math.min(99.2, Math.max(0.8, value));

export interface Point {
  x: number;
  y: number;
}

export function project(
  lat: number | null | undefined,
  lng: number | null | undefined,
): Point | null {
  if (typeof lat !== "number" || typeof lng !== "number") return null;
  if (Number.isNaN(lat) || Number.isNaN(lng)) return null;
  return {
    x: clamp(((lng - BOUNDS.west) / SPAN_LNG) * 100),
    y: clamp(((BOUNDS.north - lat) / SPAN_LAT) * 100),
  };
}

export function distanceKm(a: Point | null, b: Point | null): number | null {
  if (!a || !b) return null;
  const dx = ((a.x - b.x) / 100) * SPAN_LNG * 101.3;
  const dy = ((a.y - b.y) / 100) * SPAN_LAT * 110.9;
  return Math.sqrt(dx * dx + dy * dy);
}
