/**
 * utils/uuid.js — UUID validation helper.
 */

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Returns the value if it's a valid UUID, otherwise null.
 * Prevents "invalid input syntax for type uuid" errors when
 * tenant_id is a placeholder like 'system' or 'unknown'.
 */
export function uuidOrNull(value) {
  if (typeof value === 'string' && UUID_RE.test(value)) return value;
  return null;
}
