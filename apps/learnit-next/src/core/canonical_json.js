const TEXT_ENCODER = new TextEncoder();

export class CanonicalJsonError extends Error {
  constructor(message, path = '$') {
    super(`${message} at ${path}`);
    this.name = 'CanonicalJsonError';
    this.path = path;
  }
}

function compareCodePoints(left, right) {
  const a = Array.from(left, (character) => character.codePointAt(0));
  const b = Array.from(right, (character) => character.codePointAt(0));
  const length = Math.min(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    if (a[index] !== b[index]) return a[index] - b[index];
  }
  return a.length - b.length;
}

function encodeString(value) {
  return JSON.stringify(value.normalize('NFC'));
}

function canonicalize(value, path, root, omitRootKey) {
  if (value === null) return 'null';

  if (typeof value === 'string') return encodeString(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';

  if (typeof value === 'number') {
    if (!Number.isInteger(value) || !Number.isFinite(value)) {
      throw new CanonicalJsonError('Only finite integers are supported', path);
    }
    return Object.is(value, -0) ? '0' : String(value);
  }

  if (Array.isArray(value)) {
    return `[${value.map((entry, index) => canonicalize(entry, `${path}[${index}]`, false, omitRootKey)).join(',')}]`;
  }

  if (typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype) {
    const normalized = new Map();
    for (const originalKey of Object.keys(value)) {
      if (root && originalKey === omitRootKey) continue;
      const key = originalKey.normalize('NFC');
      if (normalized.has(key)) {
        throw new CanonicalJsonError('Object keys collide after NFC normalization', path);
      }
      normalized.set(key, originalKey);
    }

    const keys = [...normalized.keys()].sort(compareCodePoints);
    const entries = keys.map((key) => {
      const originalKey = normalized.get(key);
      const childPath = `${path}.${key}`;
      return `${encodeString(key)}:${canonicalize(value[originalKey], childPath, false, omitRootKey)}`;
    });
    return `{${entries.join(',')}}`;
  }

  throw new CanonicalJsonError('Unsupported JSON value', path);
}

export function canonicalJson(value, { omitRootKey } = {}) {
  return canonicalize(value, '$', true, omitRootKey);
}

export function canonicalBytes(value, options) {
  return TEXT_ENCODER.encode(canonicalJson(value, options));
}

function toHex(buffer) {
  return [...new Uint8Array(buffer)]
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

export async function sha256Canonical(value, options) {
  if (!globalThis.crypto?.subtle) {
    throw new Error('Web Crypto SHA-256 is unavailable in this environment');
  }
  const digest = await globalThis.crypto.subtle.digest('SHA-256', canonicalBytes(value, options));
  return `sha256:${toHex(digest)}`;
}

export async function verifyCanonicalDigest(value, digestField) {
  const declared = value?.[digestField];
  const calculated = await sha256Canonical(value, { omitRootKey: digestField });
  return {
    ok: declared === calculated,
    declared,
    calculated,
  };
}
