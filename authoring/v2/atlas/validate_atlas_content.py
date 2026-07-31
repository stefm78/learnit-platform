#!/usr/bin/env python3
"""Fail-closed Atlas 0.3 editorial validator for representative kits."""
from __future__ import annotations
import hashlib, json, pathlib, re, sys, unicodedata
try:
    import jsonschema
except ImportError as exc:
    raise SystemExit('jsonschema>=4.18 is required') from exc
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SCHEMA=ROOT/'contracts/learnit-kit-v2.schema.json'
FILES=(HERE/'nombres_complexes_atlas.json',HERE/'signaux_electriques_atlas.json')
CLASS={('activation','practice'):'practice',('comprehension','practice'):'practice',('application','practice'):'practice',('consolidation','practice'):'correction',('validation','validation'):'validation',('transfer','practice'):'transfer',('diagnostic','diagnostic'):'diagnostic'}
BASIS={'new-instance','new-context','alternate-representation'}

def canonical(v):
    if isinstance(v,dict):return {unicodedata.normalize('NFC',k):canonical(v[k]) for k in sorted(v,key=lambda x:[ord(c) for c in x])}
    if isinstance(v,list):return [canonical(x) for x in v]
    if isinstance(v,str):return unicodedata.normalize('NFC',v)
    if isinstance(v,(bool,int)) or v is None:return v
    raise ValueError('NON_CANONICAL_VALUE')

def h(domain,v):
    raw=domain.encode('utf-8')+b'\0'+json.dumps(canonical(v),ensure_ascii=False,separators=(',',':')).encode('utf-8')
    return 'sha256:'+hashlib.sha256(raw).hexdigest()

def norm(s):
    if not isinstance(s,str):raise ValueError('INVALID_VISIBLE_STRING')
    return re.sub(r'\s+',' ',unicodedata.normalize('NFC',s).strip())

def stimulus_payload(a):
    base={'type':a['type'],'prompt':norm(a['prompt'])}
    if a['type']=='qcm':
        choices={x['choiceId']:norm(x['label']) for x in a['choices']}
        if len(choices)!=len(a['choices']) or a.get('correctChoiceId') not in choices:raise ValueError('QCM_OPERATION_INVALID')
        labels=sorted(choices.values())
        if len(labels)!=len(set(labels)):raise ValueError('QCM_VISIBLE_CHOICE_COLLISION')
        base['choices']=labels
        base['answerOperation']={'kind':'select-one','correctValue':choices[a['correctChoiceId']]}
    elif a['type']=='fill':
        token_labels={x['tokenId']:norm(x['label']) for x in a['tokens']}
        if len(token_labels)!=len(a['tokens']):raise ValueError('FILL_TOKEN_COLLISION')
        slot_order=[];segments=[]
        for segment in a['segments']:
            if 'text' in segment:segments.append({'text':norm(segment['text'])})
            elif set(segment)=={'slotId'}:
                if segment['slotId'] in slot_order:raise ValueError('FILL_SLOT_COLLISION')
                slot_order.append(segment['slotId']);segments.append({'blank':len(slot_order)-1})
            else:raise ValueError('FILL_SEGMENT_INVALID')
        answers={x['slotId']:x['tokenId'] for x in a['answers']}
        if len(answers)!=len(a['answers']) or set(answers)!=set(slot_order):raise ValueError('FILL_ANSWER_MAPPING_INVALID')
        try:correct=[token_labels[answers[slot]] for slot in slot_order]
        except KeyError as exc:raise ValueError('FILL_ANSWER_TOKEN_UNKNOWN') from exc
        base['segments']=segments
        base['tokens']=sorted(token_labels.values())
        base['answerOperation']={'kind':'fill-blanks','correctValues':correct}
    else:raise ValueError('ATLAS_ACTIVITY_TYPE_UNSUPPORTED')
    return base

def stimulus(a):return h('learnit.atlas.m1.v0.3/stimulus-digest/atlas.stimulus.v1',stimulus_payload(a))

def qref(pkg,course,objective=None,activity=None):
    r={'courseRef':{'packageLineageId':pkg,'courseLineageId':course}}
    if (objective is None)==(activity is None):raise ValueError('UNQUALIFIED_REFERENCE')
    if objective is not None:r['objectiveId']=objective
    else:r['activityLineageId']=activity
    return r

def claim_material(package,course,claim):
    byid={a['activityLineageId']:a for a in course['activities']}
    try:s,t=byid[claim['sourceActivityLineageId']],byid[claim['targetActivityLineageId']]
    except KeyError as exc:raise ValueError('CLAIM_ACTIVITY_UNKNOWN') from exc
    objective=claim['objectiveId']
    if s['objectiveIds']!=[objective] or t['objectiveIds']!=[objective]:raise ValueError('CLAIM_OBJECTIVE_ACTIVITY_MISMATCH')
    if s is t or claim['sourceActivityLineageId']==claim['targetActivityLineageId']:raise ValueError('CLAIM_SOURCE_TARGET_NOT_DISTINCT')
    sd,td=stimulus(s),stimulus(t)
    if sd==td:raise ValueError('CLAIM_STIMULUS_NOT_DISTINCT')
    payload={'claimVersion':'atlas.independence.v1','objectiveRef':qref(package['packageLineageId'],course['courseLineageId'],objective=objective),'sourceActivityRef':qref(package['packageLineageId'],course['courseLineageId'],activity=claim['sourceActivityLineageId']),'targetActivityRef':qref(package['packageLineageId'],course['courseLineageId'],activity=claim['targetActivityLineageId']),'basisCode':claim['basisCode'],'sourceStimulusDigest':sd,'targetStimulusDigest':td}
    claim_id='atlas-claim-sha256:'+h('learnit.atlas.m1.v0.3/validation-claim-id',payload).split(':',1)[1]
    return sd,td,claim_id

def validate_packages(packages):
    if not isinstance(packages,list) or not packages:raise ValueError('PACKAGES_REQUIRED')
    global_packages=set();global_courses=set();global_objectives=set();global_activities=set();global_claims=set()
    schema=json.loads(SCHEMA.read_text()) if SCHEMA.exists() else None
    for p in packages:
        if schema:jsonschema.Draft202012Validator(schema).validate(p)
        if p.get('contract')!='learnit.kit.v2':raise ValueError('contract')
        if p['packageLineageId'] in global_packages:raise ValueError('DUPLICATE_PACKAGE_REF')
        global_packages.add(p['packageLineageId'])
        for course in p['courses']:
            course_key=(p['packageLineageId'],course['courseLineageId'])
            if course_key in global_courses:raise ValueError('DUPLICATE_COURSE_REF')
            global_courses.add(course_key)
            obj_ids=[o['objectiveId'] for o in course['objectives']]
            if len(obj_ids)!=len(set(obj_ids)):raise ValueError('duplicate objective')
            for oid in obj_ids:
                ref=course_key+(oid,)
                if ref in global_objectives:raise ValueError('DUPLICATE_OBJECTIVE_REF')
                global_objectives.add(ref)
            acts=course['activities'];ids=[a['activityLineageId'] for a in acts]
            if len(ids)!=len(set(ids)):raise ValueError('duplicate activity')
            grouped={o:[] for o in obj_ids}
            for idx,a in enumerate(acts):
                ref=course_key+(a['activityLineageId'],)
                if ref in global_activities:raise ValueError('DUPLICATE_ACTIVITY_REF')
                global_activities.add(ref)
                if not isinstance(a.get('estimatedMinutes'),int) or not 1<=a['estimatedMinutes']<=30:raise ValueError('ATLAS_ACTIVITY_DURATION_REQUIRED')
                pair=(a['learningPhase'],a['assessmentRole'])
                if pair not in CLASS:raise ValueError('INVALID_ACTIVITY_CLASSIFICATION')
                if len(a['objectiveIds'])!=1 or a['objectiveIds'][0] not in grouped:raise ValueError('OBJECTIVE_LINK_INVALID')
                stimulus(a)
                grouped[a['objectiveIds'][0]].append((idx,CLASS[pair],a))
            claims=course.get('atlasValidationIndependenceClaims',[])
            for objective,rows in grouped.items():
                classes=[x[1] for x in rows]
                if classes!=['practice','correction','validation','validation','transfer']:raise ValueError(f'AUTHOR_ORDER_INVALID:{objective}:{classes}')
                if any(row[2]['estimatedMinutes']>5 for row in rows[:4]):raise ValueError('PROFILE_5_HAS_NO_ADMISSIBLE_ACTIVITY')
                if len([c for c in claims if c['objectiveId']==objective])!=2:raise ValueError('CLAIM_COUNT_INVALID')
            for c in claims:
                if c.get('claimVersion')!='atlas.independence.v1' or c.get('basisCode') not in BASIS:raise ValueError('CLAIM_SHAPE_INVALID')
                sd,td,expected=claim_material(p,course,c)
                if c.get('sourceStimulusDigest')!=sd or c.get('targetStimulusDigest')!=td:raise ValueError('STIMULUS_DIGEST_INVALID')
                if c.get('claimId')!=expected:raise ValueError('CLAIM_ID_INVALID')
                if expected in global_claims:raise ValueError('DUPLICATE_CLAIM_ID')
                global_claims.add(expected)
    return True

def validate_package(p):return validate_packages([p])

def rewrite_claims(package):
    for course in package['courses']:
        for claim in course.get('atlasValidationIndependenceClaims',[]):
            sd,td,cid=claim_material(package,course,claim)
            claim['claimVersion']='atlas.independence.v1';claim['sourceStimulusDigest']=sd;claim['targetStimulusDigest']=td;claim['claimId']=cid
    return package

def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv);packages=[json.loads(path.read_text(encoding='utf-8')) for path in FILES]
    if argv==['--rewrite-claims']:
        for path,p in zip(FILES,packages):path.write_text(json.dumps(rewrite_claims(p),ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
        packages=[json.loads(path.read_text(encoding='utf-8')) for path in FILES]
    elif argv:raise SystemExit('usage: validate_atlas_content.py [--rewrite-claims]')
    validate_packages(packages)
    for path in FILES:print(f'{path.name}: PASS')
    print('OVERALL PASS')
if __name__=='__main__':main()
