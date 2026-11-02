

export function timeAgo(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "—";
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "—";
  const secs = Math.max(0, Math.round((now - then) / 1000));
  if (secs < 45) return "just now";
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins} min`;
  const hours = Math.floor(mins / 60);
  const rem = mins % 60;
  if (hours < 24) return rem ? `${hours} h ${rem} m` : `${hours} h`;
  const days = Math.floor(hours / 24);
  return `${days} d`;
}

export function timeAgoPhrase(iso: string | null | undefined, now = Date.now()): string {
  const value = timeAgo(iso, now);
  if (value === "just now" || value === "—") return value;
  return `${value} ago`;
}

export function timeUntil(iso: string | null | undefined, now = Date.now()): string | null {
  if (!iso) return null;
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return null;
  const secs = Math.round((then - now) / 1000);
  if (secs <= 0) return null;
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins} min`;
  const hours = Math.floor(mins / 60);
  const rem = mins % 60;
  if (hours < 24) return rem ? `${hours} h ${rem} m` : `${hours} h`;
  return `${Math.floor(hours / 24)} d`;
}

export function clock(iso: string | null | undefined): string {
  if (!iso) return "—:—:—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—:—:—";
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function score(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}

export function coords(
  lat: number | null | undefined,
  lng: number | null | undefined,
): string {
  if (typeof lat !== "number" || typeof lng !== "number") return "No coordinates";
  return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

export function eventLabel(type: string): string {
  const spaced = type.replace(/([a-z0-9])([A-Z])/g, "$1 $2");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1).toLowerCase();
}

export function maskPhone(phone: string | null | undefined): string {
  if (!phone) return "—";
  const digits = phone.replace(/\D/g, "");
  if (digits.length <= 4) return digits;
  return `${"*".repeat(Math.max(3, digits.length - 4))}${digits.slice(-4)}`;
}

export function prettyPhone(phone: string | null | undefined): string {
  if (!phone) return "—";
  const digits = phone.replace(/\D/g, "");
  if (digits.startsWith("92") && digits.length === 12) {
    const local = `0${digits.slice(2)}`;
    return `${local.slice(0, 4)} ${local.slice(4, 7)} ${local.slice(7)}`;
  }
  return phone;
}

export function capabilityLabel(capability: string): string {
  const map: Record<string, string> = {
    foot: "On foot",
    car: "Car",
    boat: "Boat",
    first_aid: "First aid",
  };
  return map[capability] ?? capability.replace(/_/g, " ");
}
