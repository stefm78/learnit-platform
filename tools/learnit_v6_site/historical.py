#!/usr/bin/env python3
"""LearnIT S1, local pinned R15 site reconstruction + HTTP identity inventory.

Windows v2: LF normalization of only generated Authoring index and evidence.

READ-ONLY REMOTE: HTTP GET to stefm78.github.io only; Git reads locally only.
LOCAL: create-only timestamped work directory under the current user's home.
It is NOT a complete deployed site claim, a v6 candidate, or an S1 PASS.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

MAIN = 'c7f7587c9e5beb29a123e5139c17b6448229a0cc'
STABLE = '4eebdef9fb0014c2e4a965e0c1e78d127dd712f4'
AUTHORING = 'be3d5b2635836e8ce0d9a6ecf42d573efc9ef749'
PRODUCT = '88cad160714830462234970276c808c42b4a2579'
FROZEN_PRODUCT = '6fa1acc23999b5a0b9a0b7f375a12f19ecc4e4e2'
FROZEN_QA = '6ff592af68e6cc95bd479911a09388293c5528f5'
R15_WORKFLOW_BLOB = 'bdd41ad68c86353358fc84896ba98ffc14904fb0'
BASE_URL = 'https://stefm78.github.io/learnit-platform/'
MAX_BYTES = 4 * 1024 * 1024
REPLAYS = [
    ('R10', '10fbe658175f634648baf86f7bf10320b88a3127', 'c4abc922e1d80793263557f12a3f4c2f9a7203e19a26240c914c2ab39ba97e89', 405648),
    ('R11', '934e1c7193fc6d20d408339f8a962bca6aea51a6', '4f620a570fabb669165791f36db1977b744ac82c9eb5c95654c6c402deb4b173', 407356),
    ('R12', '01a5ca9b3e8a3abd5fb9692a001bb8533065b45f', '6d7d80e577b5eeb8df0a6c560078577abcce7549fa6f70c40dc73457dc215956', 411551),
    ('R13_PREVIOUS', 'ca1f537ee435b31794282b3cf6b3c7589e736783', '6f82e74755d53bbbbbb9ef0536bd3ce4258c148a1f7f191e6ba31cb38f8faa18', 415361),
    ('R13_FINAL', '76fb8b6724d2fbcb7998b8eab92b8f2448ea8a6b', '4d95a9d1dbbdac3f8231fe6f4f27b47b62794fd33915c32f83b5792e2fb3bfe3', 412825),
    ('R14', '8cd2c27edf68bae1bb1a1a634a431a2ecbfce4e9', '0e616367600141b34ddc7ca3248bdecea67744dcd32d6008d376853c101df68d', 421465),
    ('R15', PRODUCT, '0b268c9af10677617815e821389944bf9158d1fa10a7049ebc7b0082cceec2dd', 421487),
]
STABLE_SHA = '4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7'
V6_SHA = '92115133901b50509880c2e7ad9d76816f74e30443b5f52d1cf35d935dac953b'
AUTHORING_SHA = 'fd18614c303a5233b6ca40069b548c219a65ad769442fc70886203244ce1345d'
EVIDENCE_SHA = '400a1b42c61afdefbc5eb3c08a4d7ecbe4de321fd612e1b069c63403740f1e09'


def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def execute(cmd: list[str], cwd: Path, *, quiet: bool = False) -> bytes:
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       check=False)
    if p.returncode:
        raise RuntimeError(f'{" ".join(cmd[:3])} failed: '
                           + p.stderr.decode('utf-8', 'replace')[-1600:])
    if not quiet and p.stderr:
        error_text = p.stderr.decode('utf-8', 'replace').strip()
        if error_text and 'Preparing worktree' not in error_text:
            print(error_text[:400], file=sys.stderr)
    return p.stdout


def git(repo: Path, *args: str) -> str:
    return execute(['git', *args], repo, quiet=True).decode('utf-8', 'replace').strip()


def validate(data: bytes, expected_hash: str, expected_size: int, label: str) -> None:
    actual_hash = h(data)
    if len(data) != expected_size or actual_hash != expected_hash:
        raise RuntimeError(f'{label} HASH_OR_SIZE_MISMATCH: '
                           f'{actual_hash} bytes={len(data)} vs '
                           f'{expected_hash} bytes={expected_size}')


def normalize_windows_generated_authoring_files(authoring_dir: Path) -> None:
    """Reproduce Linux Path.write_text bytes for two frozen generated outputs.

    The frozen builder creates only index.html and pages-evidence.json using
    Path.write_text, which translates LF to CRLF on Windows. No frozen source,
    copied assets or worktree files are changed. Match exact Linux digests
    afterwards (fail closed).
    """
    if os.name != 'nt':
        return
    for name in ('index.html', 'pages-evidence.json'):
        target = authoring_dir / name
        raw = target.read_bytes()
        if b'\r' in raw.replace(b'\r\n', b''):
            raise RuntimeError('HOLD: unexpected bare CR in ' + str(target))
        normalized = raw.replace(b'\r\n', b'\n')
        if raw != normalized:
            target.write_bytes(normalized)
            print('WINDOWS_LF_NORMALIZED ' + name + ' removed_CR=' + str(len(raw) - len(normalized)))


def build_html(tree: Path, output: Path, expected_hash: str,
               expected_bytes: int, label: str) -> None:
    execute([sys.executable, '-B', str(tree / 'apps/learnit-next/build.py'),
             '--output', str(output)], tree, quiet=True)
    validate(output.read_bytes(), expected_hash, expected_bytes, label)
    print(f'PASS_BUILD {label} {expected_bytes}')


def identity(data: dict) -> bytes:
    return (json.dumps(data, separators=(',', ':'), ensure_ascii=False) + '\n').encode('utf-8')


def guide(fixture: bytes, label: str) -> bytes:
    d = json.loads(fixture)
    lines = [f'Guide de réponses — Human Replay Atlas {label}',
             'Utilisez ce guide uniquement pour tester le parcours et la progression.',
             'Pour tester la correction, répondez volontairement faux à une activité practice, puis reprenez le parcours.', '']
    for course in d['courses']:
        lines += [course['title'], '=' * len(course['title'])]
        for ix, activity in enumerate(course['activities'], 1):
            lines.append(f"{ix}. {activity['prompt']}")
            if activity['type'] == 'qcm':
                by_id = {c['choiceId']: c['label'] for c in activity['choices']}
                answer = by_id[activity['correctChoiceId']]
            else:
                tokens = {t['tokenId']: t['label'] for t in activity['tokens']}
                answers = {a['slotId']: tokens[a['tokenId']] for a in activity['answers']}
                answer = ' / '.join(answers[s['slotId']] for s in activity['segments'] if 'slotId' in s)
            lines += [f'   Réponse correcte : {answer}', '']
    # Explicit LF, matching the Linux runner; no CRLF translation on Windows.
    return ('\n'.join(lines) + '\n').encode('utf-8')


def fetch_file(entry: dict) -> dict:
    rel = entry['path']
    url = BASE_URL + quote(rel, safe='/')
    try:
        req = Request(url, headers={'User-Agent': 'LearnIT-S1-ReadOnly-File-Inventory/1.0',
                                    'Cache-Control': 'no-cache'})
        with urlopen(req, timeout=30) as response:
            end = response.geturl()
            body = response.read(MAX_BYTES + 1)
            status = response.status
        p = urlsplit(end)
        if (p.scheme != 'https' or p.netloc != 'stefm78.github.io'
                or not p.path.startswith('/learnit-platform/')):
            return {'path': rel, 'url': url, 'status': 'HOLD_REDIRECT_OUT_OF_SCOPE'}
        if len(body) > MAX_BYTES:
            return {'path': rel, 'url': url, 'status': 'HOLD_OVERSIZE'}
        is_match = status == 200 and len(body) == entry['bytes'] and h(body) == entry['sha256']
        return {'path': rel, 'url': url, 'http': status,
                'remote_bytes': len(body), 'remote_sha256': h(body),
                'status': 'MATCH' if is_match else 'MISMATCH'}
    except Exception as exc:
        return {'path': rel, 'url': url, 'status': 'HOLD_HTTP_ERROR',
                'error': str(exc)[:180]}


def main() -> int:
    started = time.perf_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path.home() / 'learnit-v6-integrated-r1')
    parser.add_argument('--skip-http', action='store_true', help='Only reconstruct local site files')
    args = parser.parse_args()
    repo = args.repo.resolve(strict=True)
    if git(repo, 'rev-parse', 'HEAD') != MAIN or git(repo, 'status', '--porcelain'):
        raise RuntimeError('HOLD: exact base or clean worktree check failed')
    if git(repo, 'rev-parse', f'{MAIN}:.github/workflows/atlas-r15-human-replay-deploy.yml') != R15_WORKFLOW_BLOB:
        raise RuntimeError('HOLD: pinned R15 workflow blob drift')
    # Create once locally; neither remote writes nor repo changes.
    out = Path(tempfile.mkdtemp(prefix='learnit-s1-full-', dir=Path.home()))
    site = out / 'SITE_RECONSTRUCTION_NOT_FOR_DEPLOYMENT'
    site.mkdir()
    worktree_base = out / '_temporary_worktrees'
    worktree_base.mkdir()
    created: list[Path] = []
    finished_worktrees = False
    try:
        def add(ref: str, label: str) -> Path:
            path = worktree_base / label
            execute(['git', '-c', 'core.autocrlf=false', '-c', 'core.eol=lf',
                     'worktree', 'add', '--detach', str(path), ref], repo, quiet=True)
            created.append(path)
            if git(path, 'rev-parse', 'HEAD') != ref:
                raise RuntimeError(f'HOLD: detached worktree {label} drift')
            return path

        # The R15 deploy workflow checked out the frozen M3.1 ref for Authoring.
        wt_authoring = add(AUTHORING, 'frozen-authoring')
        authoring_dir = site / 'authoring'
        execute([sys.executable, '-B', str(wt_authoring / 'authoring/studio/pages/build_pages.py'),
                 '--output', str(authoring_dir)], wt_authoring, quiet=True)
        normalize_windows_generated_authoring_files(authoring_dir)
        validate((authoring_dir / 'index.html').read_bytes(), AUTHORING_SHA, 5091, 'Authoring index')
        wt_stable = add(STABLE, 'stable-learner')
        build_html(wt_stable, site / 'index.html', STABLE_SHA, 366412, 'STABLE')
        shutil.copyfile(site / 'index.html', site / 'learnit-next.html')

        quality = h((wt_authoring / 'authoring/v2/atlas/pedagogical_quality.py').read_bytes())
        authoring_hash = h((authoring_dir / 'index.html').read_bytes())
        deployment = {
            'schema': 'learnit.next.pages.deployment.v3',
            'learnerPromotedHead': STABLE,
            'learnerArtifactBytes': 366412,
            'learnerArtifactSha256': STABLE_SHA,
            'm3_1PromotedMain': AUTHORING,
            'frozenProductHead': FROZEN_PRODUCT,
            'frozenQaHead': FROZEN_QA,
            'qualityEngineSha256': quality,
            'authoringIndexSha256': authoring_hash,
            'authoringPath': '/authoring/',
            'learnerIndexByteIdentity': 'PASS',
            'stableAuthoringPublication': True,
            'humanUxDebtIssue': 272,
            'runtimeBackendDependencyAdded': False,
        }
        deployment_bytes = identity(deployment)
        validate(deployment_bytes, EVIDENCE_SHA, 753, 'R15 deployment-evidence')
        (site / 'deployment-evidence.json').write_bytes(deployment_bytes)
        print('PASS_BUILD AUTHORING + DEPLOYMENT_EVIDENCE')

        for name, ref, expected_sha, expected_size in REPLAYS:
            tree = add(ref, name)
            directory = site / 'human-replay' / ref
            fixture_dir = directory / 'fixtures'
            fixture_dir.mkdir(parents=True)
            build_html(tree, directory / 'index.html', expected_sha, expected_size, name)
            shutil.copyfile(directory / 'index.html', directory / 'learnit-next.html')
            is_legacy = name in ('R10', 'R11')
            fixture_name = ('signaux_electriques.json' if is_legacy
                            else 'nombres_complexes_atlas.json')
            relative_source = ('authoring/v2/golden/signaux_electriques.json' if is_legacy
                               else 'authoring/v2/atlas/nombres_complexes_atlas.json')
            fixture_bytes = (tree / relative_source).read_bytes()
            (fixture_dir / fixture_name).write_bytes(fixture_bytes)
            meta = {
                'schema': 'learnit.atlas.human-replay.v1',
                'issue': 352,
                'pullRequest': 354,
                'productHead': ref,
                'learnerArtifactBytes': expected_size,
                'learnerArtifactSha256': expected_sha,
                'fixture': 'fixtures/' + fixture_name,
                'fixtureSha256': h(fixture_bytes),
            }
            if not is_legacy:
                label = {'R13_PREVIOUS': 'R13-PREVIOUS',
                         'R13_FINAL': 'R13-FINAL'}.get(name, name)
                guide_name = 'nombres_complexes_atlas-answer-guide.txt'
                guide_bytes = guide(fixture_bytes, label)
                (fixture_dir / guide_name).write_bytes(guide_bytes)
                meta['answerGuide'] = 'fixtures/' + guide_name
                meta['answerGuideSha256'] = h(guide_bytes)
            meta.update({'promotion': False, 'humanGateRequired': True,
                         'learnerUxPass': False})
            (directory / 'identity.json').write_bytes(identity(meta))

        # This V6 replay was observed live, but is not defined in the R15 workflow.
        # Its identity, fixtures and other possible companion files remain UNKNOWN.
        v6_tree = add(MAIN, 'v6-source')
        v6_dir = site / 'human-replay' / MAIN
        v6_dir.mkdir(parents=True)
        build_html(v6_tree, v6_dir / 'index.html', V6_SHA, 627042, 'V6_OBSERVED_INDEX_ONLY')

        entries = []
        for f in sorted(site.rglob('*')):
            if not f.is_file():
                continue
            relative = f.relative_to(site).as_posix()
            data = f.read_bytes()
            entries.append({'path': relative, 'bytes': len(data),
                            'sha256': h(data),
                            'provenance': ('v6_observed_index_only' if relative.startswith(f'human-replay/{MAIN}/')
                                           else 'r15_workflow_reconstruction')})
        print('LOCAL_RECONSTRUCTED_FILES=' + str(len(entries)))
        results = []
        if not args.skip_http:
            with ThreadPoolExecutor(max_workers=4) as pool:
                future_map = {pool.submit(fetch_file, item): item['path'] for item in entries}
                for future in as_completed(future_map):
                    results.append(future.result())
            results.sort(key=lambda x: x['path'])
        count_matches = sum(item['status'] == 'MATCH' for item in results)
        count_failures = sum(item['status'] != 'MATCH' for item in results)
        report = {
            'schema': 'learnit.local.s1-site-file-inventory.v1',
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'base_commit': MAIN,
            'r15_workflow_git_blob_sha1': R15_WORKFLOW_BLOB,
            'mode': 'READ_ONLY_REMOTE_LOCAL_CREATE_ONLY',
            'remote_mutations': 0,
            'candidate_created': False,
            'local_site_dir': str(site),
            'file_count': len(entries),
            'files': entries,
            'http_match': count_matches,
            'http_checked': len(results),
            'http_nonmatch': count_failures,
            'http_results': results,
            'limitations': [
                'R15 workflow reconstructed from frozen refs, not an inventory of a Pages deployment archive.',
                'V6 replay reconstructed as index.html only; its identity/fixtures/companions remain UNVERIFIED.',
                '51 historical ZIP entries are not interpreted as 51 site paths; ZIP not compared in this tool.',
                'External URL consumers, dynamic requests and additional unpublished/published files are not exhaustively known.',
                'No browser, IndexedDB, recovery, Pages environment or publisher safety tested.',
            ],
            's1_complete': False,
            'elapsed_monotonic_seconds': round(time.perf_counter() - started, 3),
        }
        manifest = out / 'S1_SITE_FILE_MANIFEST.json'
        with manifest.open('x', encoding='utf-8', newline='\n') as fp:
            json.dump(report, fp, ensure_ascii=False, indent=2)
            fp.write('\n')
        print(f'HTTP_FILE_IDENTITIES={count_matches}/{len(results)}')
        print(f'HTTP_NONMATCH={count_failures}')
        print('S1_TOTAL=NOT_PROVEN')
        print('GITHUB_MUTATIONS=0 / ONEDRIVE_MUTATIONS=0')
        print('EVIDENCE=' + str(manifest))
        print('SITE=' + str(site))
        finished_worktrees = True
        return 0 if count_failures == 0 else 2
    finally:
        for wt in reversed(created):
            subprocess.run(['git', 'worktree', 'remove', '--force', str(wt)],
                           cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            worktree_base.rmdir()
        except OSError:
            pass
        if not finished_worktrees:
            print('HOLD: reconstruction did not complete. Local scratch directory: ' + str(out),
                  file=sys.stderr)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('HOLD: ' + str(exc), file=sys.stderr)
        sys.exit(2)
