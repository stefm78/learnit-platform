const REQUIRED_METHODS = Object.freeze(['projectCourse']);

export function assertLearningProjectionPort(port) {
  if (port == null) return null;
  for (const method of REQUIRED_METHODS) {
    if (typeof port?.[method] !== 'function') {
      throw new TypeError(`Learning projection port is missing ${method}()`);
    }
  }
  return port;
}
