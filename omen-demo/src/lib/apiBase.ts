/**
 * Base URL for OMEN API. Normalizes invalid URLs (e.g. http://:8000 -> localhost).
 */
function normalizeOmenApiBase(): string {
  const raw = (import.meta.env.VITE_OMEN_API_URL as string) || 'http://localhost:8000/api/v1';
  try {
    const u = new URL(raw);
    if (!u.hostname || u.hostname === '') {
      return 'http://localhost:8000/api/v1';
    }
    return raw;
  } catch {
    return 'http://localhost:8000/api/v1';
  }
}

export const OMEN_API_BASE = normalizeOmenApiBase();

/** Base URL without /api/v1 for health checks. */
export function getOmenBaseUrl(): string {
  const base = OMEN_API_BASE.replace(/\/api\/v1\/?$/, '');
  return base || 'http://localhost:8000';
}
