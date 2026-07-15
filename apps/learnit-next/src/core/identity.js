export const UUID_V4_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

export function isUuidV4(value) {
  return typeof value === 'string' && UUID_V4_PATTERN.test(value);
}

export function createInstallationId() {
  if (typeof globalThis.crypto?.randomUUID !== 'function') {
    throw new Error('crypto.randomUUID is unavailable');
  }
  const id = globalThis.crypto.randomUUID().toLowerCase();
  if (!isUuidV4(id)) throw new Error('Generated installation identifier is not a UUID v4');
  return id;
}

export function assertUuidV4(value, label) {
  if (!isUuidV4(value)) {
    throw new TypeError(`${label} must be a lowercase UUID v4`);
  }
  return value;
}

export function addUniqueId(registry, category, value, path, errors) {
  const categoryRegistry = registry.get(category) ?? new Map();
  registry.set(category, categoryRegistry);
  const previousPath = categoryRegistry.get(value);
  if (previousPath) {
    errors.push({
      code: 'duplicate_id',
      path,
      message: `${category} duplicates ${previousPath}`,
    });
  } else {
    categoryRegistry.set(value, path);
  }
}
