const MODULE_PATHS = Object.freeze({
  clock: 'apps/learnit-next/src/core/atlas_clock.js',
  events: 'apps/learnit-next/src/core/atlas_events.js',
  evidence: 'apps/learnit-next/src/core/atlas_evidence.js',
  claimAuthority: 'apps/learnit-next/src/core/atlas_claim_authority.js',
  memory: 'apps/learnit-next/src/core/atlas_memory.js',
  planner: 'apps/learnit-next/src/core/atlas_planner.js',
  projection: 'apps/learnit-next/src/core/atlas_projection.js',
  recommendation: 'apps/learnit-next/src/core/atlas_recommendation.js',
  storagePort: 'apps/learnit-next/src/ports/atlas_storage.js',
  indexedDb: 'apps/learnit-next/src/adapters/atlas_indexeddb.js',
  today: 'apps/learnit-next/src/ui/atlas_today.js',
  session: 'apps/learnit-next/src/ui/atlas_session.js',
  summary: 'apps/learnit-next/src/ui/atlas_summary.js',
  rewards: 'apps/learnit-next/src/ui/atlas_rewards.js',
});

function registry() {
  const value = globalThis.__LEARNIT_ATLAS_CJS__;
  if (!value || typeof value.require !== 'function') {
    throw new Error('ATLAS_BROWSER_COMMONJS_REGISTRY_MISSING');
  }
  return value;
}

export function installAtlasRuntime() {
  const loader = registry();
  const modules = {};

  for (const [name, modulePath] of Object.entries(MODULE_PATHS)) {
    const moduleValue = loader.require(modulePath);
    if (!moduleValue || typeof moduleValue !== 'object') {
      throw new Error(`ATLAS_MODULE_INVALID: ${modulePath}`);
    }
    modules[name] = moduleValue;
  }

  const frozenModules = Object.freeze(modules);
  const api = Object.freeze({
    schemaVersion: 'learnit.atlas.browser-integration.v1',
    ready: true,
    moduleNames: Object.freeze(Object.keys(frozenModules)),
    modules: frozenModules,
    status() {
      return Object.freeze({
        ready: true,
        schemaVersion: 'learnit.atlas.browser-integration.v1',
        moduleNames: Object.freeze(Object.keys(frozenModules)),
      });
    },
  });

  Object.defineProperty(globalThis, '__LEARNIT_ATLAS_M1__', {
    configurable: false,
    enumerable: false,
    writable: false,
    value: api,
  });

  return api;
}
