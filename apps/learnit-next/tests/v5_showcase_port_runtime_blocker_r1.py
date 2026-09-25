#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HIST="982b86bf86e18b39926736f92a16be40ba47f60b"
V4="showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v4.json"
V4_BLOB="7d90c619b05d4dbea1a1b5674be82cc0dcdcdeec"
EXPECTED=["lesson","flashcard","matching","qcm","qcm","flashcard","order","matching","qcm","qcm"]
FROZEN={"apps/learnit-next/src/integration/atlas/surface.js":"aea13ae66fdeeddae6a32b46f8c53875f6a754ad","apps/learnit-next/src/integration/atlas/session.js":"98d8348e98c2068c0cb29f0e4f0a0e0493b00b5d","apps/learnit-next/src/ui/render.js":"af3ac83a5cf1455d982f6c73cfc8377c7cbc6ef8"}
for path,expected in FROZEN.items():
    actual=subprocess.check_output(["git","hash-object",path],cwd=ROOT,text=True).strip()
    assert actual==expected,(path,actual,expected)
subprocess.run(["git","fetch","--force","--no-tags","origin",HIST],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
assert subprocess.check_output(["git","rev-parse",f"{HIST}:{V4}"],cwd=ROOT,text=True).strip()==V4_BLOB
v4=json.loads(subprocess.check_output(["git","show",f"{HIST}:{V4}"],cwd=ROOT))
acts=v4["courses"][0]["activities"]
assert len(v4["courses"])==1 and len(acts)==10 and v4["courses"][0]["estimatedMinutes"]==39
assert [a["type"] for a in acts]==EXPECTED
assert all(a["type"]!="constructed" and "acceptedResponses" not in a for a in acts)
candidate=dict(v4)
candidate["contract"]="learnit.kit.v5"
candidate["packageRevisionId"]="9062f1a1-f01f-42c7-90fb-ed4bdeaeb579"
candidate["packageRevisionDigest"]="sha256:"+"0"*64
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/"candidate.json"
    p.write_text(json.dumps(candidate,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    node=r"""
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
globalThis.crypto ??= webcrypto;
import {sha256Canonical,validatePackageObject} from './apps/learnit-next/src/core/contract.js';
import {buildInstallationPlan} from './apps/learnit-next/src/core/import.js';
import {projectAtlasActivityPresentation} from './apps/learnit-next/src/integration/atlas/session.js';
import {renderAtlasActivityMarkup} from './apps/learnit-next/src/ui/render.js';
const kit=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));
kit.packageRevisionDigest=await sha256Canonical(kit,{omitRootKey:'packageRevisionDigest'});
const vr=await validatePackageObject(kit);
assert.equal(vr.ok,true,JSON.stringify(vr.errors));
const plan=buildInstallationPlan(kit,new Date('2026-09-25T10:30:00.000Z'));
assert.equal(plan.courses.length,1);
assert.equal(plan.courses[0].activities.length,10);
const first=kit.courses[0].activities[0];
assert.equal(first.type,'lesson');
const projected=projectAtlasActivityPresentation(first,{assets:kit.assets??[],contract:kit.contract});
assert.equal(projected.type,'lesson');
assert.throws(()=>renderAtlasActivityMarkup(projected),/ATLAS_ACTIVITY_TYPE_UNSUPPORTED: lesson/);
console.log('V5_IMPORT_TRANSIENT_CANDIDATE: PASS');
console.log('FIRST_ACTIVITY_V5_PROJECTION: lesson');
console.log('ATLAS_RENDERER_FIRST_ACTIVITY: BLOCKED');
"""
    out=subprocess.run(["node","--input-type=module","-e",node,str(p)],cwd=ROOT,check=True,text=True,capture_output=True)
    print(out.stdout,end="")
surface=(ROOT/"apps/learnit-next/src/integration/atlas/surface.js").read_text(encoding="utf-8")
assert "const ATLAS_SUPPORTED_ACTIVITY_TYPES = new Set(['qcm', 'fill']);" in surface
unsupported=sorted(set(EXPECTED)-{"qcm","fill"})
assert unsupported==["flashcard","lesson","matching","order"]
print("ACTIVITY_COUNT: 10")
print("DURATION_MINUTES: 39")
print("ATLAS_SURFACE_SUPPORTED_TYPES: qcm,fill")
print("EXACT_REQUIRED_UNSUPPORTED_TYPES: "+",".join(unsupported))
print("ATLAS_V8_FULL_JOURNEY: BLOCKED")
print("REFERENCES_RUNTIME_FETCH: NONE")
print("UPSTREAM_PRODUCT_MUTATION: NONE")
print("HOLD_UPSTREAM_RUNTIME_DEFECT")
