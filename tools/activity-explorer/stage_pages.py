#!/usr/bin/env python3
"""Create-only local staging: immutable 52-route published site + 8 canonical explorer routes.

This script NEVER publishes, edits source files, writes to GitHub/OneDrive, or
changes the LearnIT renderer. It requires an already-qualified exact published
52-route site input (the deployed Oct 31 CSP artifact); it is not an installer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

PUBLISHED_ROOT_SHA = '4390d2f525ba1779e681a30f7c853f391094b9d1b85ce7b13f230efcf5be01eb'
PUBLISHED_ROOT_BYTES = 626416
HISTORICAL_COUNT = 50
EXPECTED = 'tools/learnit_v6_site/expected_files.json'
EXPLORER = ('tools/activity-explorer/index.html',
            'tools/activity-explorer/explorer.js',
            'tools/activity-explorer/explorer.css')
CANONICAL = ('apps/learnit-next/src/integration/atlas/activity_projection.js',
             'apps/learnit-next/src/ui/activity_presenters.js',
             'apps/learnit-next/src/ui/media.js',
             'apps/learnit-next/src/core/activity_semantics.js',
             'apps/learnit-next/src/styles.css')
NEW_ROUTES = (*EXPLORER, *CANONICAL)
ROOT_ALIASES = ('index.html', 'learnit-next.html')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_file(root: Path, rel: str) -> bytes:
    target = root / rel
    if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(root.resolve()):
        raise RuntimeError('HOLD missing/unsafe file: ' + rel)
    return target.read_bytes()


def stage(repo: Path, site: Path, output: Path) -> dict:
    repo = repo.resolve(strict=True)
    site = site.resolve(strict=True)
    output = output.absolute()
    if output.exists() or output.is_symlink() or output == site or site in output.parents or repo in output.parents:
        raise RuntimeError('HOLD output conflict or unsafe destination')
    m = json.loads(check_file(repo, EXPECTED))
    expected = {x['path']: x for x in m['files']}
    if m.get('schema') != 'learnit.v6.site.expected-files.r1' or len(expected) != 52:
        raise RuntimeError('HOLD frozen 52-route manifest mismatch')
    actual_paths = {p.relative_to(site).as_posix() for p in site.rglob('*') if p.is_file()}
    if actual_paths != set(expected):
        raise RuntimeError('HOLD published site inventory != 52 frozen paths')
    for path, item in expected.items():
        b = check_file(site, path)
        golden_sha = PUBLISHED_ROOT_SHA if path in ROOT_ALIASES else item['sha256']
        golden_size = PUBLISHED_ROOT_BYTES if path in ROOT_ALIASES else item['bytes']
        if sha(b) != golden_sha or len(b) != golden_size:
            raise RuntimeError('HOLD published route drift: ' + path)
    if set(NEW_ROUTES) & actual_paths or len(set(NEW_ROUTES)) != 8:
        raise RuntimeError('HOLD route collision')
    additions = {}
    for path in NEW_ROUTES:
        b = check_file(repo, path)
        if not b or len(b) > 1_000_000:
            raise RuntimeError('HOLD empty/oversized new resource: ' + path)
        additions[path] = {'bytes': len(b), 'sha256': sha(b)}
    if b"from '../../apps/learnit-next/src/integration/atlas/activity_projection.js'" not in check_file(repo, EXPLORER[1]):
        raise RuntimeError('HOLD explorer missing canonical projection import')
    if b"from '../../apps/learnit-next/src/ui/activity_presenters.js'" not in check_file(repo, EXPLORER[1]):
        raise RuntimeError('HOLD explorer missing canonical presenter import')
    if b"../../apps/learnit-next/src/styles.css" not in check_file(repo, EXPLORER[0]):
        raise RuntimeError('HOLD explorer missing canonical stylesheet')
    output.parent.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix='.learnit-explorer-stage-', dir=output.parent))
    try:
        shutil.copytree(site, scratch / 'site')
        for path in NEW_ROUTES:
            target = scratch / 'site' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(check_file(repo, path))
        inventory = sorted(p.relative_to(scratch / 'site').as_posix() for p in (scratch / 'site').rglob('*') if p.is_file())
        if set(inventory) != set(expected) | set(NEW_ROUTES) or len(inventory) != 60:
            raise RuntimeError('HOLD staged inventory differs from exact 60 routes')
        for path in inventory:
            old = check_file(site, path) if path in expected else check_file(repo, path)
            new = check_file(scratch / 'site', path)
            if old != new:
                raise RuntimeError('HOLD unexpected changed route: ' + path)
        result = {'schema': 'learnit.v6.activity-explorer.local-stage.v1',
                  'status': 'PASS_LOCAL_ONLY_NO_PUBLICATION',
                  'published_routes_preserved': 52, 'new_routes': additions,
                  'route_count': 60, 'publisher_modified': False,
                  'learner_renderer_modified': False}
        (scratch / 'manifest.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        # Atomic no-overwrite rename of staging directory (on same filesystem).
        if output.exists(): raise RuntimeError('HOLD output conflict')
        scratch.rename(output)
        return result
    finally:
        if scratch.exists(): shutil.rmtree(scratch)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--published-site', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    opts = ap.parse_args()
    try:
        result = stage(opts.repo, opts.published_site, opts.output)
        print(json.dumps(result, sort_keys=True)); return 0
    except Exception as exc:
        print('HOLD: ' + str(exc), file=sys.stderr); return 2

if __name__ == '__main__': raise SystemExit(main())
