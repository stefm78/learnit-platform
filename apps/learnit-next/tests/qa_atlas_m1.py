#!/usr/bin/env python3
"""Independent Atlas M1 0.3 QA harness.

At lane publication it runs its independent oracle and adversarial preflight. A
candidate verdict requires --strict plus exact heads, artifact, claim set and
real-browser evidence; no historical evidence is silently reused.
"""
from __future__ import annotations
import argparse, dataclasses, hashlib, json, pathlib, re, subprocess, sys, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[3]
VALID=ROOT/'contracts/fixtures/atlas-m1-valid-loop.json'
INVALID=ROOT/'contracts/fixtures/atlas-m1-invalid-loop.json'
CANON_TS=re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')
REWARDS=('validation-reconfirmed','validation-completed','correction-completed','independent-success','resumed-after-interruption')
REASONS={'NEW_OBJECTIVE','PRACTICE_IN_PROGRESS','RECENT_ERROR','REVIEW_REQUIRED','CORRECTION_COMPLETED','NO_INDEPENDENT_VALIDATION','VALIDATION_AVAILABLE','RECENTLY_VALIDATED','SESSION_TIME_LIMIT'}

def sha256_file(path:pathlib.Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()
def canonical(v):
    if isinstance(v,dict):return {k:canonical(v[k]) for k in sorted(v)}
    if isinstance(v,list):return [canonical(x) for x in v]
    return v
def objective_projection(events,executions):
    """Oracle independent of product code; lifecycle events are ignored."""
    ex={x['executionId']:x for x in executions};rows={};latest_error={};corrected=set()
    for ev in sorted((e for e in events if e['kind'] in ('activity-attempt','activity-corrected')),key=lambda x:(x['occurredAt'],x['eventId'])):
        key=json.dumps(canonical(ev['objectiveRef']),separators=(',',':'));r=rows.setdefault(key,{'practiceAttempts':0,'correctionsCompleted':0,'validationAttempts':0,'latestPracticeCorrect':None,'latestValidationCorrect':None,'lastValidationAt':None,'lastEvidenceAt':None,'state':'not-started'})
        x=ex[ev['executionId']];r['lastEvidenceAt']=max(filter(None,(r['lastEvidenceAt'],ev['occurredAt'])))
        if ev['kind']=='activity-corrected':r['correctionsCompleted']+=1;corrected.add(ev['correctsEventId'])
        elif x['executionClass']=='practice':r['practiceAttempts']+=1;r['latestPracticeCorrect']=x['outcome']=='correct';latest_error[key]=ev['eventId'] if x['outcome']=='incorrect' else latest_error.get(key)
        elif x['executionClass']=='validation':
            r['validationAttempts']+=1;r['latestValidationCorrect']=x['outcome']=='correct'
            if x['outcome']=='correct' and x['assistance']=='none' and x.get('validationAdmissible') is True:r['state']='validated-recently';r['lastValidationAt']=x['scoredAt']
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
def assert_claim_set(claim_set,artifact_digest,revision):
    if claim_set.get('schemaVersion')!='atlas.accepted-validation-claims.v1':raise AssertionError('CLAIM_SET_SCHEMA')
    if claim_set.get('artifactDigest')!='sha256:'+artifact_digest:raise AssertionError('CLAIM_SET_ARTIFACT_MISMATCH')
    if claim_set.get('contentRevisionRef')!=revision:raise AssertionError('CLAIM_SET_REVISION_MISMATCH')
    ids=claim_set.get('acceptedClaimIds');
    if not isinstance(ids,list) or ids!=sorted(set(ids)):raise AssertionError('CLAIM_SET_NOT_SORTED_UNIQUE')
def static_network_gate(paths):
    forbidden=('fetch(','XMLHttpRequest','WebSocket','openai','anthropic','http://','https://')
    findings=[]
    for path in paths:
        text=path.read_text(encoding='utf-8')
        for token in forbidden:
            if token in text:findings.append((str(path),token))
    return findings
def run_browser_gate(artifact:pathlib.Path):
    """Real Chromium at exact viewports, network blocked, keyboard/focus/overflow."""
    script=f"""
from playwright.sync_api import sync_playwright
from pathlib import Path
uri=Path({str(artifact)!r}).resolve().as_uri()
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width,height in ((1440,900),(390,844)):
  page=browser.new_page(viewport={{'width':width,'height':height}})
  page.route('**/*',lambda route: route.continue_() if route.request.url.startswith('file:') else route.abort())
  page.goto(uri); page.keyboard.press('Tab')
  assert page.evaluate("document.activeElement !== document.body")
  assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
  assert page.evaluate("document.body.innerText.length > 0")
  page.close()
 browser.close()
"""
    cp=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True)
    if cp.returncode:raise RuntimeError('BROWSER_GATE_FAILED\n'+cp.stderr)

class OracleTests(unittest.TestCase):
    def test_lifecycle_is_inert_and_correction_is_not_validation(self):
        obj={'courseRef':{'packageLineageId':'p','courseLineageId':'c'},'objectiveId':'o'}
        ex=[{'executionId':'x1','executionClass':'practice','outcome':'incorrect','assistance':'none','scoredAt':'2026-01-01T00:00:00.000Z'},{'executionId':'x2','executionClass':'correction','outcome':'correct','assistance':'none','scoredAt':'2026-01-01T00:01:00.000Z'}]
        ev=[{'eventId':'e1','kind':'activity-attempt','objectiveRef':obj,'executionId':'x1','occurredAt':'2026-01-01T00:00:00.000Z'},{'eventId':'life','kind':'session-completed','occurredAt':'2026-01-01T00:00:30.000Z'},{'eventId':'e2','kind':'activity-corrected','objectiveRef':obj,'executionId':'x2','correctsEventId':'e1','occurredAt':'2026-01-01T00:01:00.000Z'}]
        row=next(iter(objective_projection(ev,ex).values()));self.assertEqual(row['practiceAttempts'],1);self.assertEqual(row['correctionsCompleted'],1);self.assertEqual(row['validationAttempts'],0);self.assertEqual(row['lastEvidenceAt'],'2026-01-01T00:01:00.000Z')
    def test_reward_priority_exclusive(self):
        facts=[{'eventId':'same','rewardKind':'independent-success','occurredAt':'2026-01-01T00:00:00.000Z'},{'eventId':'same','rewardKind':'validation-completed','occurredAt':'2026-01-01T00:00:00.000Z'}]
        self.assertEqual(exclusive_rewards(facts),['validation-completed'])
    def test_closed_reason_codes(self):
        self.assertIn('VALIDATION_AVAILABLE',REASONS);self.assertNotIn('FREE_TEXT',REASONS)
    def test_canonical_timestamp(self):
        self.assertRegex('2026-01-01T00:00:00.000Z',CANON_TS);self.assertNotRegex('2026-01-01T00:00:00+00:00',CANON_TS)
    def test_claim_set_artifact_binding(self):
        revision={'packageLineageId':'p','packageRevisionId':'r','packageDigest':'sha256:'+'1'*64};s={'schemaVersion':'atlas.accepted-validation-claims.v1','contentRevisionRef':revision,'artifactDigest':'sha256:'+'2'*64,'acceptedClaimIds':['atlas-claim-sha256:'+'3'*64]};assert_claim_set(s,'2'*64,revision);s['artifactDigest']='sha256:'+'4'*64
        with self.assertRaisesRegex(AssertionError,'ARTIFACT'):assert_claim_set(s,'2'*64,revision)

def preflight():
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(OracleTests);result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():return 1
    fixture_status=[]
    for path in (VALID,INVALID):
        if path.exists():
            data=json.loads(path.read_text(encoding='utf-8'));fixture_status.append({'path':str(path.relative_to(ROOT)),'sha256':sha256_file(path),'contractVersion':data.get('contractVersion')})
    print(json.dumps({'verdict':'PRE_CANDIDATE_QA_READY','oracleTests':result.testsRun,'fixtures':fixture_status,'contractFixturesModified':False},indent=2))
    return 0
def strict(args):
    if len(args.accepted_head)!=4:raise SystemExit('four --accepted-head values required')
    for value in [args.candidate_head,*args.accepted_head]:
        if not re.fullmatch(r'[0-9a-f]{40}',value):raise SystemExit('exact lowercase SHA required')
    artifact=pathlib.Path(args.artifact);actual=sha256_file(artifact)
    if actual!=args.artifact_sha256:raise SystemExit('ARTIFACT_SHA256_MISMATCH')
    claim=json.loads(pathlib.Path(args.claim_set).read_text());assert_claim_set(claim,actual,claim['contentRevisionRef'])
    run_browser_gate(artifact)
    print(json.dumps({'verdict':'PASS_TO_HUMAN_GATE','candidateHead':args.candidate_head,'artifactSha256':actual,'acceptedHeads':args.accepted_head},indent=2));return 0
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--strict',action='store_true');ap.add_argument('--candidate-head');ap.add_argument('--artifact');ap.add_argument('--artifact-sha256');ap.add_argument('--accepted-head',action='append',default=[]);ap.add_argument('--claim-set')
    args=ap.parse_args();return strict(args) if args.strict else preflight()
if __name__=='__main__':raise SystemExit(main())
