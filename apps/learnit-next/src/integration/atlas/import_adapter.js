/*
 * Student V0.1 keeps this adapter as a stable composition seam. Contract
 * admission and Atlas extension validation now live in core/contract.js for
 * the explicit v2/v3/v4 discriminators, so this layer must not rewrite kits.
 */
export function createAtlasCompatibleImportService(_storage, base) {
  if (!base || typeof base !== 'object') {
    throw new TypeError('A core import service is required');
  }
  for (const method of ['validatePackage', 'previewImport', 'importPackage']) {
    if (typeof base[method] !== 'function') {
      throw new TypeError(`Core import service is missing ${method}()`);
    }
  }
  return Object.freeze({
    validatePackage: payload => base.validatePackage(payload),
    previewImport: payload => base.previewImport(payload),
    importPackage: payload => base.importPackage(payload),
  });
}
