#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
import json

from support import ROOT
from contract_source_tree import runtime_fingerprint, normalized_runtime_js_fingerprint

OUT = ROOT.parent.parent / 'docs' / 'evidence' / 'architecture' / 'first-storage-seam' / 'fingerprint-diagnostic.json'
PORT = 'src/scripts/core/runtime_parts/04_local_storage_port.js'
BASE_COMMIT = '746cd0a7abac219da58543fe82831123c0ef9fd4'


def main() -> int:
    config_path = ROOT / 'dev' / 'release_config.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    simulated = deepcopy(config)
    equivalence = simulated.setdefault('baseline_equivalence', {})
    ignored = list(equivalence.get('ignored_script_paths', []))
    if PORT not in ignored:
        ignored.append(PORT)
    equivalence['ignored_script_paths'] = ignored

    measured_runtime = runtime_fingerprint()
    measured_normalized = normalized_runtime_js_fingerprint(simulated)
    protected_normalized = str(config.get('baseline_equivalence', {}).get('runtime_js_normalized_sha256', ''))
    previous_runtime = str(config.get('runtime_fingerprint', ''))
    payload = {
        'schema': 'learnit.first_storage_seam_fingerprint_diagnostic.v1',
        'baseCommit': BASE_COMMIT,
        'diagnosticMode': 'disposable-unmerged',
        'portPath': PORT,
        'previousRuntimeFingerprint': previous_runtime,
        'measuredRuntimeFingerprint': measured_runtime,
        'protectedNormalizedRuntimeFingerprint': protected_normalized,
        'measuredNormalizedRuntimeFingerprintWithRelocatedPortIgnored': measured_normalized,
        'runtimeFingerprintChanged': measured_runtime != previous_runtime,
        'normalizedFingerprintMatches': measured_normalized == protected_normalized,
        'authorizedReleaseConfigChange': {
            'addIgnoredScriptPath': PORT,
            'replaceRuntimeFingerprintWith': measured_runtime,
            'preserveNormalizedRuntimeFingerprint': protected_normalized,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload['runtimeFingerprintChanged'] and payload['normalizedFingerprintMatches'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
