export class AtlasClockError extends TypeError {
  constructor(message, code = 'INVALID_ATLAS_CLOCK') {
    super(message);
    this.name = 'AtlasClockError';
    this.code = code;
  }
}

function asDate(value, label) {
  const date = value instanceof Date ? new Date(value.getTime()) : new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new AtlasClockError(`${label} must be a valid timestamp`, 'INVALID_ATLAS_TIMESTAMP');
  }
  return date;
}

export function normalizeAtlasTimestamp(value, label = 'timestamp') {
  if (typeof value !== 'string' && !(value instanceof Date)) {
    throw new AtlasClockError(`${label} must be an ISO timestamp`, 'INVALID_ATLAS_TIMESTAMP');
  }
  return asDate(value, label).toISOString();
}

export function compareAtlasTimestamps(left, right) {
  return normalizeAtlasTimestamp(left, 'left timestamp')
    .localeCompare(normalizeAtlasTimestamp(right, 'right timestamp'));
}

export function assertAtlasClock(clock) {
  if (typeof clock?.now !== 'function') {
    throw new AtlasClockError('Atlas clock must expose now()');
  }
  normalizeAtlasTimestamp(clock.now(), 'clock.now()');
  return clock;
}

export function createSystemAtlasClock({ now = () => new Date() } = {}) {
  if (typeof now !== 'function') {
    throw new AtlasClockError('System clock now provider must be a function');
  }
  return Object.freeze({
    now() {
      return normalizeAtlasTimestamp(now(), 'system clock value');
    },
  });
}

export function createControlledAtlasClock(initialTimestamp) {
  let current = normalizeAtlasTimestamp(initialTimestamp, 'initialTimestamp');
  const clock = {
    now() {
      return current;
    },
    set(timestamp) {
      current = normalizeAtlasTimestamp(timestamp, 'controlled clock timestamp');
      return current;
    },
    advance(milliseconds) {
      if (!Number.isFinite(milliseconds) || milliseconds < 0) {
        throw new AtlasClockError(
          'controlled clock advance must be a non-negative finite number',
          'INVALID_ATLAS_CLOCK_ADVANCE',
        );
      }
      current = new Date(Date.parse(current) + milliseconds).toISOString();
      return current;
    },
    snapshot() {
      return Object.freeze({ now: current });
    },
  };
  return Object.freeze(clock);
}
