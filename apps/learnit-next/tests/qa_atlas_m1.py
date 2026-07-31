#!/usr/bin/env python3
"""Independent, fail-closed Atlas M1 0.3 QA harness.

Preflight validates the oracle and immutable contract fixtures. Strict mode is
reserved for an exact integrated candidate and binds candidate commit, four
accepted lane heads, artifact, provenance manifest, accepted claim set, source
network gate, Chromium flows and IndexedDB fault injection.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, re, subprocess, sys, unittest, unicodedata
ROOT=pathlib.Path(__file__).resolve().parents[3]
VALID=ROOT/'contracts/fixtures/atlas-m1-valid-loop.json'
INVALID=ROOT/'contracts/fixtures/atlas-m1-invalid-loop.json'
EXPECTED_FIXTURE_SHA256={
 'contracts/fixtures/atlas-m1-valid-loop.json':'2abc0ecf8eb1f4b7afcb1e7a010015e9549bfbf0a4a6dcc4379a65c2c5fda46a',
 'contracts/fixtures/atlas-m1-invalid-loop.json':'dca06d3df5cdb0c0492f38e787996ca95f760f6cbdd0c72f8bed5e1a498cca0d',
}
CANON_TS=re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')
SHA40=re.compile(r'^[0-9a-f]{40}$')
DIGEST=re.compile(r'^sha256:[0-9a-f]{64}$')
CLAIM_ID=re.compile(r'^atlas-claim-sha256:[0-9a-f]{64}$')
REWARDS=('validation-reconfirmed','validation-completed','correction-completed','independent-success','resumed-after-interruption')
REASONS={'NEW_OBJECTIVE','PRACTICE_IN_PROGRESS','RECENT_ERROR','REVIEW_REQUIRED','CORRECTION_COMPLETED','NO_INDEPENDENT_VALIDATION','VALIDATION_AVAILABLE','RECENTLY_VALIDATED','SESSION_TIME_LIMIT'}
LANE_PATHS={
 'learning':('apps/learnit-next/src/core/atlas_evidence.js','apps/learnit-next/src/core/atlas_recommendation.js','apps/learnit-next/src/core/atlas_planner.js','apps/learnit-next/tests/atlas_m1_learning.py'),
 'core':('apps/learnit-next/src/core/atlas_events.js','apps/learnit-next/src/core/atlas_projection.js','apps/learnit-next/src/core/atlas_clock.js','apps/learnit-next/src/ports/atlas_storage.js','apps/learnit-next/src/adapters/atlas_indexeddb.js','apps/learnit-next/tests/atlas_m1_core.py'),
 'experience':('apps/learnit-next/src/ui/atlas_today.js','apps/learnit-next/src/ui/atlas_session.js','apps/learnit-next/src/ui/atlas_summary.js','apps/learnit-next/src/ui/atlas_rewards.js','apps/learnit-next/src/atlas.css','apps/learnit-next/tests/atlas_m1_experience.py'),
 'content':('authoring/v2/atlas/README.md','authoring/v2/atlas/nombres_complexes_atlas.json','authoring/v2/atlas/signaux_electriques_atlas.json','authoring/v2/atlas/validate_atlas_content.py','apps/learnit-next/tests/atlas_m1_content.py'),
}

def sha256_file(path:pathlib.Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def canonical(v):
    if v is None or isinstance(v,bool):return v
    if isinstance(v,str):return unicodedata.normalize('NFC',v)
    if isinstance(v,int):return v
    if isinstance(v,float):raise AssertionError('NON_CANONICAL_NUMBER')
    if isinstance(v,dict):return {unicodedata.normalize('NFC',k):canonical(v[k]) for k in sorted(v,key=lambda s:[ord(c) for c in s])}
    if isinstance(v,list):return [canonical(x) for x in v]
    raise AssertionError('NON_CANONICAL_VALUE')

def objective_projection(events,executions):
    """Independent oracle using only contractual fields; lifecycle is inert."""
    ex={x['executionId']:x for x in executions};rows={};latest_error={};corrected=set()
    for ev in sorted((e for e in events if e['kind'] in ('activity-attempt','activity-corrected')),key=lambda x:(x['occurredAt'],x['eventId'])):
        key=json.dumps(canonical(ev['objectiveRef']),ensure_ascii=False,separators=(',',':'));r=rows.setdefault(key,{'practiceAttempts':0,'correctionsCompleted':0,'validationAttempts':0,'latestPracticeCorrect':None,'latestValidationCorrect':None,'lastValidationAt':None,'lastEvidenceAt':None,'state':'not-started'})
        x=ex[ev['executionId']];r['lastEvidenceAt']=max(filter(None,(r['lastEvidenceAt'],ev['occurredAt'])))
        if ev['kind']=='activity-corrected':r['correctionsCompleted']+=1;corrected.add(ev['correctsEventId'])
        elif x['executionClass']=='practice':r['practiceAttempts']+=1;r['latestPracticeCorrect']=x['outcome']=='correct';latest_error[key]=ev['eventId'] if x['outcome']=='incorrect' else latest_error.get(key)
        elif x['executionClass']=='validation':
            r['validationAttempts']+=1;r['latestValidationCorrect']=x['outcome']=='correct'
            admissible=x['action'] in ('attempt-validation','maintain-recent-validation') and x['assistance']=='none'
            if x['outcome']=='correct' and admissible:r['state']='validated-recently';r['lastValidationAt']=x['scoredAt']
            elif x['outcome']=='incorrect':r['state']='review-needed'
    for key,r in rows.items():
        if latest_error.get(key) and latest_error[key] not in corrected:r['state']='review-needed'
        elif r['state']=='not-started':r['state']='ready-for-validation' if r['latestPracticeCorrect'] else 'training'
    return rows

def exclusive_rewards(facts):
    allocated=set();out=[]
    candidates=sorted(facts,key=lambda f:(REWARDS.index(f['rewardKind']),f['occurredAt'],f['eventId']))
    for f in candidates:
        if f['eventId'] in allocated:continue
        allocated.add(f['eventId']);out.append(f['rewardKind'])
    return out

def assert_closed(obj,required):
    if not isinstance(obj,dict) or set(obj)!=set(required):raise AssertionError('OBJECT_NOT_CLOSED')

def assert_claim_set(claim_set,artifact_digest,revision,oracle_version):
    required=('schemaVersion','contentRevisionRef','oracleVersion','artifactDigest','acceptedClaimIds')
    assert_closed(claim_set,required)
    if claim_set['schemaVersion']!='atlas.accepted-validation-claims.v1':raise AssertionError('CLAIM_SET_SCHEMA')
    if claim_set['oracleVersion']!=oracle_version or not oracle_version:raise AssertionError('CLAIM_SET_ORACLE_MISMATCH')
    if claim_set['artifactDigest']!='sha256:'+artifact_digest:raise AssertionError('CLAIM_SET_ARTIFACT_MISMATCH')
    if canonical(claim_set['contentRevisionRef'])!=canonical(revision):raise AssertionError('CLAIM_SET_REVISION_MISMATCH')
    ids=claim_set['acceptedClaimIds']
    if not isinstance(ids,list) or ids!=sorted(set(ids)) or any(not CLAIM_ID.fullmatch(x) for x in ids):raise AssertionError('CLAIM_SET_NOT_SORTED_UNIQUE')

def run_git(root,*args,check=True):
    cp=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True)
    if check and cp.returncode:raise RuntimeError('GIT_FAILURE: '+' '.join(args)+'\n'+cp.stderr)
    return cp.stdout.strip()

def parse_heads(values):
    result={}
    for value in values:
        if '=' not in value:raise SystemExit('--accepted-head requires lane=sha')
        lane,sha=value.split('=',1)
        if lane not in LANE_PATHS or lane in result or not SHA40.fullmatch(sha):raise SystemExit('invalid or duplicate accepted head')
        result[lane]=sha
    if set(result)!=set(LANE_PATHS):raise SystemExit('exact learning/core/experience/content heads required')
    return result

def bind_candidate_to_heads(repo:pathlib.Path,candidate:str,heads:dict[str,str]):
    if run_git(repo,'cat-file','-t',candidate)!='commit':raise AssertionError('CANDIDATE_COMMIT_MISSING')
    for lane,head in heads.items():
        if run_git(repo,'cat-file','-t',head)!='commit':raise AssertionError(f'{lane.upper()}_HEAD_MISSING')
        for path in LANE_PATHS[lane]:
            accepted=run_git(repo,'rev-parse',f'{head}:{path}')
            candidate_blob=run_git(repo,'rev-parse',f'{candidate}:{path}')
            if accepted!=candidate_blob:raise AssertionError(f'{lane.upper()}_BLOB_MISMATCH:{path}')

def assert_artifact_provenance(path:pathlib.Path,candidate:str,heads:dict[str,str],artifact_sha:str):
    obj=json.loads(path.read_text(encoding='utf-8'))
    required=('schemaVersion','candidateHead','artifactSha256','acceptedHeads','buildCommands','cleanCheckout','networkBlocked')
    assert_closed(obj,required)
    if obj['schemaVersion']!='atlas.artifact-provenance.v1' or obj['candidateHead']!=candidate or obj['artifactSha256']!=artifact_sha or obj['acceptedHeads']!=heads:raise AssertionError('ARTIFACT_PROVENANCE_MISMATCH')
    if obj['cleanCheckout'] is not True or obj['networkBlocked'] is not True or not isinstance(obj['buildCommands'],list) or not obj['buildCommands']:raise AssertionError('ARTIFACT_PROVENANCE_INCOMPLETE')

def static_network_gate(paths):
    forbidden=('fetch(','XMLHttpRequest','WebSocket','openai','anthropic','http://','https://')
    findings=[]
    for path in paths:
        text=path.read_text(encoding='utf-8')
        for token in forbidden:
            if token in text:findings.append((str(path),token))
    return findings

def run_browser_gate(artifact:pathlib.Path):
    """Exercise exact Atlas hooks in Chromium at both frozen viewports."""
    script=f"""
from playwright.sync_api import sync_playwright
from pathlib import Path
uri=Path({str(artifact)!r}).resolve().as_uri()
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width,height in ((1440,900),(390,844)):
  context=browser.new_context(viewport={{'width':width,'height':height}})
  page=context.new_page(); blocked=[]
  page.route('**/*',lambda route: route.continue_() if route.request.url.startswith('file:') else (blocked.append(route.request.url),route.abort())[1])
  page.goto(uri)
  assert page.evaluate("typeof window.LearnItAtlasM1 === 'object'")
  assert page.evaluate("typeof window.LearnItAtlasM1.qaScenario === 'function'")
  result=page.evaluate("window.LearnItAtlasM1.qaScenario({{faultInjection:true,closeReopen:true,assistance:true}})")
  assert result['started'] and result['rawSubmissionOnly'] and result['progressAfterCommitOnly']
  assert result['assistancePersistedBeforeDisplay'] and result['assistanceIrreversible']
  assert result['closeReopenResumed'] and result['faultInjectionAllOrZero']
  page.keyboard.press('Tab');assert page.evaluate("document.activeElement !== document.body")
  assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
  assert not blocked
  context.close()
 browser.close()
"""
    cp=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True)
    if cp.returncode:raise RuntimeError('BROWSER_GATE_FAILED\n'+cp.stderr)

class OracleTests(unittest.TestCase):
    def test_lifecycle_inert_and_correction_not_validation(self):
        obj={'courseRef':{'packageLineageId':'p','courseLineageId':'c'},'objectiveId':'o'}
        ex=[{'executionId':'x1','executionClass':'practice','action':'start-practice','outcome':'incorrect','assistance':'none','scoredAt':'2026-01-01T00:00:00.000Z'},{'executionId':'x2','executionClass':'correction','action':'correct-practice','outcome':'correct','assistance':'none','scoredAt':'2026-01-01T00:01:00.000Z'}]
        ev=[{'eventId':'e1','kind':'activity-attempt','objectiveRef':obj,'executionId':'x1','occurredAt':'2026-01-01T00:00:00.000Z'},{'eventId':'life','kind':'session-completed','occurredAt':'2026-01-01T00:00:30.000Z'},{'eventId':'e2','kind':'activity-corrected','objectiveRef':obj,'executionId':'x2','correctsEventId':'e1','occurredAt':'2026-01-01T00:01:00.000Z'}]
        row=next(iter(objective_projection(ev,ex).values()));self.assertEqual((row['practiceAttempts'],row['correctionsCompleted'],row['validationAttempts']),(1,1,0));self.assertEqual(row['lastEvidenceAt'],'2026-01-01T00:01:00.000Z')
    def test_validation_uses_contractual_action_not_private_flag(self):
        obj={'courseRef':{'packageLineageId':'p','courseLineageId':'c'},'objectiveId':'o'}
        x={'executionId':'x','executionClass':'validation','action':'attempt-validation','outcome':'correct','assistance':'none','scoredAt':'2026-01-01T00:00:00.000Z'}
        ev={'eventId':'e','kind':'activity-attempt','objectiveRef':obj,'executionId':'x','occurredAt':'2026-01-01T00:00:00.000Z'}
        self.assertEqual(next(iter(objective_projection([ev],[x]).values()))['state'],'validated-recently')
        x['validationAdmissible']=False
        self.assertEqual(next(iter(objective_projection([ev],[x]).values()))['state'],'validated-recently')
    def test_reward_priority_exclusive(self):
        facts=[{'eventId':'same','rewardKind':'independent-success','occurredAt':'2026-01-01T00:00:00.000Z'},{'eventId':'same','rewardKind':'validation-completed','occurredAt':'2026-01-01T00:00:00.000Z'}]
        self.assertEqual(exclusive_rewards(facts),['validation-completed'])
    def test_closed_reason_codes(self):self.assertIn('VALIDATION_AVAILABLE',REASONS);self.assertNotIn('FREE_TEXT',REASONS)
    def test_canonical_timestamp(self):self.assertRegex('2026-01-01T00:00:00.000Z',CANON_TS);self.assertNotRegex('2026-01-01T00:00:00+00:00',CANON_TS)
    def test_claim_set_full_binding(self):
        revision={'packageLineageId':'p','packageRevisionId':'r','packageDigest':'sha256:'+'1'*64};s={'schemaVersion':'atlas.accepted-validation-claims.v1','contentRevisionRef':revision,'oracleVersion':'atlas.qa.oracle.v1','artifactDigest':'sha256:'+'2'*64,'acceptedClaimIds':['atlas-claim-sha256:'+'3'*64]};assert_claim_set(s,'2'*64,revision,'atlas.qa.oracle.v1')
        for key in ('oracleVersion','artifactDigest'):
            bad=dict(s);bad.pop(key)
            with self.assertRaises(AssertionError):assert_claim_set(bad,'2'*64,revision,'atlas.qa.oracle.v1')
    def test_fixture_bytes_are_authoritative(self):
        for rel,expected in EXPECTED_FIXTURE_SHA256.items():
            path=ROOT/rel
            if path.exists():self.assertEqual(sha256_file(path),expected)

def fixture_report():
    rows=[];unchanged=True
    for rel,expected in EXPECTED_FIXTURE_SHA256.items():
        path=ROOT/rel;actual=sha256_file(path) if path.exists() else None;rows.append({'path':rel,'expectedSha256':expected,'actualSha256':actual,'unchanged':actual==expected});unchanged &= actual==expected
    return rows,unchanged

def preflight():
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(OracleTests);result=unittest.TextTestRunner(verbosity=2).run(suite)
    rows,unchanged=fixture_report()
    print(json.dumps({'verdict':'PRE_CANDIDATE_QA_READY' if result.wasSuccessful() and unchanged else 'CHANGES_REQUIRED','oracleTests':result.testsRun,'fixtures':rows,'contractFixturesModified':not unchanged},indent=2))
    return 0 if result.wasSuccessful() and unchanged else 1

def strict(args):
    if not all((args.candidate_head,args.artifact,args.artifact_sha256,args.claim_set,args.content_revision,args.oracle_version,args.artifact_provenance,args.repo_root,args.source_root)):raise SystemExit('strict mode requires all exact inputs')
    if not SHA40.fullmatch(args.candidate_head) or not re.fullmatch(r'[0-9a-f]{64}',args.artifact_sha256):raise SystemExit('invalid candidate or artifact digest')
    heads=parse_heads(args.accepted_head);repo=pathlib.Path(args.repo_root).resolve();bind_candidate_to_heads(repo,args.candidate_head,heads)
    artifact=pathlib.Path(args.artifact).resolve();actual=sha256_file(artifact)
    if actual!=args.artifact_sha256:raise SystemExit('ARTIFACT_SHA256_MISMATCH')
    assert_artifact_provenance(pathlib.Path(args.artifact_provenance),args.candidate_head,heads,actual)
    revision=json.loads(pathlib.Path(args.content_revision).read_text(encoding='utf-8'));claim=json.loads(pathlib.Path(args.claim_set).read_text(encoding='utf-8'));assert_claim_set(claim,actual,revision,args.oracle_version)
    source_root=pathlib.Path(args.source_root).resolve();source_paths=[source_root/p for paths in LANE_PATHS.values() for p in paths if (source_root/p).exists()]
    findings=static_network_gate(source_paths)
    if findings:raise SystemExit('STATIC_NETWORK_GATE_FAILED:'+json.dumps(findings))
    _,unchanged=fixture_report()
    if not unchanged:raise SystemExit('CONTRACT_FIXTURES_MODIFIED')
    run_browser_gate(artifact)
    print(json.dumps({'verdict':'PASS_TO_HUMAN_GATE','candidateHead':args.candidate_head,'artifactSha256':actual,'acceptedHeads':heads,'oracleVersion':args.oracle_version,'contractFixturesModified':False,'staticNetworkGate':'PASS','browserAndFaultInjection':'PASS'},indent=2));return 0

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--strict',action='store_true');ap.add_argument('--candidate-head');ap.add_argument('--artifact');ap.add_argument('--artifact-sha256');ap.add_argument('--accepted-head',action='append',default=[]);ap.add_argument('--claim-set');ap.add_argument('--content-revision');ap.add_argument('--oracle-version');ap.add_argument('--artifact-provenance');ap.add_argument('--repo-root');ap.add_argument('--source-root')
    args=ap.parse_args();return strict(args) if args.strict else preflight()
if __name__=='__main__':raise SystemExit(main())
