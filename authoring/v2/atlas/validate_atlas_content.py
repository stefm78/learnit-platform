#!/usr/bin/env python3
"""Fail-closed Atlas 0.3 editorial validator for the two representative kits."""
from __future__ import annotations
import copy, hashlib, json, pathlib, re, sys
try:
    import jsonschema
except ImportError as exc:
    raise SystemExit('jsonschema>=4.18 is required') from exc
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SCHEMA=ROOT/'contracts/learnit-kit-v2.schema.json'
FILES=(HERE/'nombres_complexes_atlas.json',HERE/'signaux_electriques_atlas.json')
CLASS={('activation','practice'):'practice',('comprehension','practice'):'practice',('application','practice'):'practice',('consolidation','practice'):'correction',('validation','validation'):'validation',('transfer','practice'):'transfer',('diagnostic','diagnostic'):'diagnostic'}
def canonical(v):
    if isinstance(v,dict):return {k:canonical(v[k]) for k in sorted(v)}
    if isinstance(v,list):return [canonical(x) for x in v]
    return v
def h(domain,v):
    raw=domain.encode()+b'\0'+json.dumps(canonical(v),ensure_ascii=False,separators=(',',':')).encode()
    return 'sha256:'+hashlib.sha256(raw).hexdigest()
def norm(s):return re.sub(r'\s+',' ',s.strip())
def stimulus(a):
    base={'type':a['type'],'prompt':norm(a['prompt'])}
    if a['type']=='qcm':base['choices']=sorted(norm(x['label']) for x in a['choices'])
    else:
        base['segments']=[('text',norm(x['text'])) if 'text'in x else ('slot',x['slotId']) for x in a['segments']]
        base['tokens']=sorted(norm(x['label']) for x in a['tokens'])
    return h('learnit.atlas.m1.v0.3/stimulus-digest/atlas.stimulus.v1',base)
def qref(pkg,course,objective=None,activity=None):
    r={'courseRef':{'packageLineageId':pkg,'courseLineageId':course}}
    if objective:r['objectiveId']=objective
    if activity:r['activityLineageId']=activity
    return r
def validate_package(p):
    if SCHEMA.exists():jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).validate(p)
    if p.get('contract')!='learnit.kit.v2':raise ValueError('contract')
    for course in p['courses']:
        obj_ids=[o['objectiveId'] for o in course['objectives']]
        if len(obj_ids)!=len(set(obj_ids)):raise ValueError('duplicate objective')
        acts=course['activities'];ids=[a['activityLineageId'] for a in acts]
        if len(ids)!=len(set(ids)):raise ValueError('duplicate activity')
        grouped={o:[] for o in obj_ids}
        for idx,a in enumerate(acts):
            if not isinstance(a.get('estimatedMinutes'),int) or not 1<=a['estimatedMinutes']<=30:raise ValueError('ATLAS_ACTIVITY_DURATION_REQUIRED')
            pair=(a['learningPhase'],a['assessmentRole'])
            if pair not in CLASS:raise ValueError('INVALID_ACTIVITY_CLASSIFICATION')
            if len(a['objectiveIds'])!=1 or a['objectiveIds'][0] not in grouped:raise ValueError('OBJECTIVE_LINK_INVALID')
            grouped[a['objectiveIds'][0]].append((idx,CLASS[pair],a))
        claims=course.get('atlasValidationIndependenceClaims',[])
        for objective,rows in grouped.items():
            classes=[x[1] for x in rows]
            if classes!=['practice','correction','validation','validation','transfer']:raise ValueError(f'AUTHOR_ORDER_INVALID:{objective}:{classes}')
            if rows[0][2]['estimatedMinutes']>5 or rows[1][2]['estimatedMinutes']>5 or rows[2][2]['estimatedMinutes']>5:raise ValueError('PROFILE_5_HAS_NO_ADMISSIBLE_ACTIVITY')
            related=[c for c in claims if c['objectiveId']==objective]
            if len(related)!=2:raise ValueError('CLAIM_COUNT_INVALID')
        byid={a['activityLineageId']:a for a in acts}
        for c in claims:
            s,t=byid[c['sourceActivityLineageId']],byid[c['targetActivityLineageId']]
            if s is t or c['sourceActivityLineageId']==c['targetActivityLineageId']:raise ValueError('CLAIM_SOURCE_TARGET_NOT_DISTINCT')
            sd,td=stimulus(s),stimulus(t)
            if c['sourceStimulusDigest']!=sd or c['targetStimulusDigest']!=td or sd==td:raise ValueError('STIMULUS_DIGEST_INVALID')
            payload={'claimVersion':'atlas.independence.v1','objectiveRef':qref(p['packageLineageId'],course['courseLineageId'],objective=c['objectiveId']),'sourceActivityRef':qref(p['packageLineageId'],course['courseLineageId'],activity=c['sourceActivityLineageId']),'targetActivityRef':qref(p['packageLineageId'],course['courseLineageId'],activity=c['targetActivityLineageId']),'basisCode':c['basisCode'],'sourceStimulusDigest':sd,'targetStimulusDigest':td}
            expected='atlas-claim-sha256:'+h('learnit.atlas.m1.v0.3/validation-claim-id',payload).split(':',1)[1]
            if c['claimId']!=expected:raise ValueError('CLAIM_ID_INVALID')
            if norm(s['prompt']).casefold()==norm(t['prompt']).casefold():raise ValueError('COSMETIC_VALIDATION_VARIANT')
    return True
def main():
    for path in FILES:
        validate_package(json.loads(path.read_text(encoding='utf-8')))
        print(f'{path.name}: PASS')
    print('OVERALL PASS')
if __name__=='__main__':main()
