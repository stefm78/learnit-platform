#!/usr/bin/env python3
"""Deterministic ATLAS-CORE lane tests with no browser, network or package install."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

BASELINE = "58e39e8917006058fdf177a5daa37535f5e2c78d"
ALLOWED = {
    "apps/learnit-next/src/core/atlas_events.js",
    "apps/learnit-next/src/core/atlas_projection.js",
    "apps/learnit-next/src/core/atlas_clock.js",
    "apps/learnit-next/src/ports/atlas_storage.js",
    "apps/learnit-next/src/adapters/atlas_indexeddb.js",
    "apps/learnit-next/tests/atlas_m1_core.py",
}
ROOT = Path(os.environ.get("ATLAS_CORE_TREE", Path(__file__).resolve().parents[3])).resolve()

NODE = r"""
import assert from 'node:assert/strict';
import {createControlledAtlasClock, createSystemAtlasClock} from './src/core/atlas_clock.js';
import {canonicalAtlasJson, createLearningEvent, mergeLearningEventJournals, normalizeLearningEvent} from './src/core/atlas_events.js';
import {projectAllObjectiveEvidence, projectObjectiveEvidence} from './src/core/atlas_projection.js';
import {ATLAS_EXPORT_KIND, ATLAS_INDEXED_DB_NAME, createAtlasExportEnvelope, normalizeAtlasResumeState} from './src/ports/atlas_storage.js';
import {createIndexedDbAtlasStorage} from './src/adapters/atlas_indexeddb.js';
const cp = structuredClone;

class Target { constructor(){this.l=new Map()} addEventListener(t,f,o={}){const a=this.l.get(t)||[];a.push({f,once:!!o.once});this.l.set(t,a)} emit(t){for(const x of [...(this.l.get(t)||[])]){x.f({type:t,target:this});if(x.once){const a=this.l.get(t);a.splice(a.indexOf(x),1)}}} }
class Req extends Target { constructor(){super();this.result=undefined;this.error=null} }
const token=k=>JSON.stringify(k); const key=(v,p)=>Array.isArray(p)?p.map(x=>v[x]):v[p];
class Store { constructor(tx,r){this.tx=tx;this.r=r} op(fn){return this.tx.op(fn)} add(v){return this.op(()=>{v=cp(v);const k=key(v,this.r.keyPath),t=token(k);if(this.r.v.has(t))throw Error('ConstraintError');this.r.v.set(t,v);return k})} put(v){return this.op(()=>{v=cp(v);const k=key(v,this.r.keyPath);this.r.v.set(token(k),v);return k})} get(k){return this.op(()=>cp(this.r.v.get(token(k))))} getAll(){return this.op(()=>[...this.r.v.values()].map(x=>cp(x)))} delete(k){return this.op(()=>{this.r.v.delete(token(k))})} count(){return this.op(()=>this.r.v.size)} }
class Tx extends Target { constructor(db,n){super();this.db=db;this.n=n;this.p=0;this.a=false;this.done=false;this.error=null;this.timer=null;this.schedule()} objectStore(n){if(!this.n.includes(n)||!this.db.stores.has(n))throw Error(`Unknown store ${n}`);return new Store(this,this.db.stores.get(n))} op(fn){if(this.a||this.done)throw Error('TransactionInactiveError');const r=new Req();this.p++;queueMicrotask(()=>{if(this.a)return;try{r.result=fn();r.emit('success')}catch(e){r.error=e;this.error=e;r.emit('error');this.abort()}finally{this.p--;this.schedule()}});return r} schedule(){if(this.a||this.done||this.timer)return;this.timer=setTimeout(()=>{this.timer=null;if(!this.a&&!this.done&&this.p===0){this.done=true;this.emit('complete')}else this.schedule()},0)} abort(){if(this.a||this.done)return;this.a=true;if(this.timer)clearTimeout(this.timer);this.timer=null;queueMicrotask(()=>this.emit('abort'))} }
class DB extends Target { constructor(r){super();this.r=r} get objectStoreNames(){return{contains:n=>this.r.stores.has(n)}} createObjectStore(n,o){this.r.stores.set(n,{keyPath:o.keyPath,v:new Map()});return{}} transaction(n){return new Tx(this.r,Array.isArray(n)?n:[n])} close(){} }
class Factory { constructor(){this.d=new Map()} open(n,v){const q=new Req();queueMicrotask(()=>{try{let r=this.d.get(n),u=!r||v>r.version;if(!r){r={version:v,stores:new Map()};this.d.set(n,r)}if(v<r.version)throw Error('VersionError');r.version=v;q.result=new DB(r);if(u)q.emit('upgradeneeded');q.emit('success')}catch(e){q.error=e;q.emit('error')}});return q} }

const base={sessionId:'s1',courseLineageId:'c1',objectiveId:'o1',activityLineageId:'a1',metadata:{}};
const ev=(id,at,kind,x={})=>normalizeLearningEvent({eventId:id,eventVersion:1,occurredAt:at,kind,sessionId:x.sessionId||base.sessionId,metadata:x.metadata||{},...x});
const att=(id,at,role,outcome,assist='none',x={})=>ev(id,at,'activity-attempt',{...base,assessmentRole:role,outcome,assistance:assist,...x});
const fix=(id,at)=>ev(id,at,'activity-corrected',{...base,assessmentRole:'practice',outcome:'completed',assistance:'review'});
const resume=(id,at,pos)=>normalizeAtlasResumeState({resumeVersion:1,sessionId:id,savedAt:at,payload:{position:pos}});
const results=[]; async function test(name,fn){try{await fn();results.push({name,status:'PASS'})}catch(e){results.push({name,status:'FAIL',error:String(e?.stack||e)})}}

await test('01 clocks and immutable kind validation',()=>{const c=createControlledAtlasClock('2026-07-29T10:00:00Z');assert.equal(c.advance(1000),'2026-07-29T10:00:01.000Z');assert.throws(()=>c.advance(-1));assert.equal(createSystemAtlasClock({now:()=>new Date('2026-07-29T11:00:00Z')}).now(),'2026-07-29T11:00:00.000Z');const src={eventId:'e',eventVersion:1,occurredAt:'2026-07-29T10:00:00Z',kind:'session-started',sessionId:'s',metadata:{x:{y:1}}};const e=normalizeLearningEvent(src);src.metadata.x.y=9;assert.equal(e.metadata.x.y,1);assert.throws(()=>{e.metadata.x.y=2},TypeError);assert.throws(()=>ev('bad','2026-07-29T10:00:00Z','session-started',{objectiveId:'fake'}),/non-applicable/);assert.throws(()=>ev('bad','2026-07-29T10:00:00Z','activity-corrected',{...base,assessmentRole:'validation',outcome:'completed',assistance:'review'}),/practice/)});
await test('02 controlled creation and journal conflict',()=>{const e=createLearningEvent({kind:'session-started',sessionId:'s',metadata:{}},{clock:createControlledAtlasClock('2026-07-29T10:00:00Z'),eventIdFactory:()=> 'generated'});assert.equal(e.eventId,'generated');const a=ev('b','2026-07-29T10:00:01Z','session-started'),b=ev('a','2026-07-29T10:00:01Z','session-started');assert.deepEqual(mergeLearningEventJournals([a],[b,cp(a)]).map(x=>x.eventId),['a','b']);assert.throws(()=>mergeLearningEventJournals([a],[{...cp(a),metadata:{changed:true}}]),/conflicting immutable content/)});
await test('03 projection replay preserves correction and validation boundaries',()=>{const h=[att('p1','2026-07-29T10:00:00Z','practice','incorrect'),fix('f1','2026-07-29T10:01:00Z'),att('p2','2026-07-29T10:02:00Z','practice','correct')];let p=projectObjectiveEvidence('o1',h);assert.equal(p.state,'ready-for-validation');assert.equal(p.correctionsCompleted,1);assert.equal(p.validationAttempts,0);h.push(att('v1','2026-07-29T10:03:00Z','validation','correct'));p=projectObjectiveEvidence('o1',h);assert.equal(p.state,'validated-recently');assert.deepEqual(p,projectObjectiveEvidence('o1',[...h].reverse()));h.push(att('p3','2026-07-29T10:04:00Z','practice','incorrect'));assert.equal(projectObjectiveEvidence('o1',h).state,'review-needed')});
await test('04 projections include declared not-started objectives',()=>{const p=projectAllObjectiveEvidence([att('p','2026-07-29T10:00:00Z','practice','correct','none',{objectiveId:'z'})],['a']);assert.deepEqual(p.map(x=>x.objectiveId),['a','z']);assert.equal(p[0].state,'not-started')});
await test('05 isolated journal survives close and rejects mutation',async()=>{const f=new Factory(),clock=createControlledAtlasClock('2026-07-29T12:00:00Z');let s=createIndexedDbAtlasStorage({indexedDbApi:f,clock});const a=ev('s','2026-07-29T10:00:00Z','session-started'),b=att('p','2026-07-29T10:01:00Z','practice','incorrect');assert.deepEqual(await s.appendEvents([a,b]),{added:2,existing:0,total:2});await s.close();s=createIndexedDbAtlasStorage({indexedDbApi:f,clock});assert.deepEqual((await s.listEvents()).map(x=>x.eventId),['s','p']);await assert.rejects(s.appendEvents([{...cp(a),metadata:{tamper:true}}]),/conflicting immutable content/);assert.equal((await s.listEvents()).length,2)});
await test('06 resume, deterministic export and reopen',async()=>{const f=new Factory(),clock=createControlledAtlasClock('2026-07-29T12:00:00Z');let s=createIndexedDbAtlasStorage({indexedDbApi:f,clock});await s.saveResumeState(resume('r1','2026-07-29T10:00:00Z',1));await s.saveResumeState(resume('r2','2026-07-29T10:05:00Z',2));const x=await s.exportAtlasData(),y=await s.exportAtlasData();assert.equal(canonicalAtlasJson(x),canonicalAtlasJson(y));assert.equal(x.kind,ATLAS_EXPORT_KIND);assert.equal(x.activeSessionId,'r2');await s.close();s=createIndexedDbAtlasStorage({indexedDbApi:f,clock});assert.equal((await s.loadActiveResumeState()).payload.position,2)});
await test('07 import merges local and exported facts without loss',async()=>{const clock=createControlledAtlasClock('2026-07-29T12:00:00Z');const remote=createIndexedDbAtlasStorage({indexedDbApi:new Factory(),clock});await remote.appendEvents([ev('remote','2026-07-29T10:00:00Z','session-started')]);await remote.saveResumeState(resume('rr','2026-07-29T10:10:00Z',4));const payload=await remote.exportAtlasData();const local=createIndexedDbAtlasStorage({indexedDbApi:new Factory(),clock});await local.appendEvents([ev('local','2026-07-29T09:00:00Z','session-started')]);await local.saveResumeState(resume('lr','2026-07-29T09:10:00Z',1));const r=await local.importAtlasData(payload);assert.equal(r.totalEvents,2);assert.equal(r.totalResumeStates,2);assert.equal(r.activeSessionId,'rr');assert.deepEqual((await local.listEvents()).map(x=>x.eventId),['local','remote'])});
await test('08 conflicting event import is atomic',async()=>{const clock=createControlledAtlasClock('2026-07-29T12:00:00Z'),s=createIndexedDbAtlasStorage({indexedDbApi:new Factory(),clock});const a=ev('same','2026-07-29T10:00:00Z','session-started');await s.appendEvents([a]);const x=createAtlasExportEnvelope({events:[{...cp(a),metadata:{bad:true}},ev('new','2026-07-29T10:01:00Z','session-started')],resumeStates:[],activeSessionId:null},{clock});await assert.rejects(s.importAtlasData(x),/conflicting immutable content/);assert.deepEqual((await s.listEvents()).map(e=>e.eventId),['same'])});
await test('09 resume conflicts are explicit and newer checkpoints win',async()=>{const clock=createControlledAtlasClock('2026-07-29T12:00:00Z'),s=createIndexedDbAtlasStorage({indexedDbApi:new Factory(),clock});await s.saveResumeState(resume('r','2026-07-29T10:00:00Z',1));let x=createAtlasExportEnvelope({events:[],resumeStates:[resume('r','2026-07-29T10:00:00Z',9)],activeSessionId:'r'},{clock});await assert.rejects(s.importAtlasData(x),/conflicts at identical savedAt/);x=createAtlasExportEnvelope({events:[],resumeStates:[resume('r','2026-07-29T10:01:00Z',2)],activeSessionId:'r'},{clock});await s.importAtlasData(x);assert.equal((await s.getResumeState('r')).payload.position,2)});
await test('10 clearing resume cannot erase events and report is Atlas-only',async()=>{const s=createIndexedDbAtlasStorage({indexedDbApi:new Factory(),clock:createControlledAtlasClock('2026-07-29T12:00:00Z')});await s.appendEvents([ev('e','2026-07-29T10:00:00Z','session-started')]);await s.saveResumeState(resume('r','2026-07-29T10:01:00Z',1));await s.clearResumeState('r');assert.equal(await s.loadActiveResumeState(),null);assert.equal((await s.listEvents()).length,1);const r=await s.storageReport();assert.equal(r.indexedDbName,'learnit_atlas_m1_v1');assert.equal(r.counts.learningEvents,1);assert.notEqual(ATLAS_INDEXED_DB_NAME,'learnit_next_v1')});

const failed=results.filter(x=>x.status!=='PASS');console.log(JSON.stringify({tests:results.length,passed:results.length-failed.length,failed},null,2));if(failed.length)process.exitCode=1;
"""


class AtlasCore(unittest.TestCase):
    def test_node_suite(self) -> None:
        if shutil.which("node") is None:
            self.skipTest("Node.js is required")
        source = ROOT / "apps" / "learnit-next"
        files = [
            "src/core/atlas_clock.js", "src/core/atlas_events.js",
            "src/core/atlas_projection.js", "src/ports/atlas_storage.js",
            "src/adapters/atlas_indexeddb.js",
        ]
        with tempfile.TemporaryDirectory(prefix="atlas-core-") as tmp:
            dst = Path(tmp)
            (dst / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
            for rel in files:
                target = dst / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / rel, target)
            harness = dst / "harness.mjs"
            harness.write_text(textwrap.dedent(NODE), encoding="utf-8")
            run = subprocess.run(["node", str(harness)], cwd=dst, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 timeout=120, check=False)
            self.assertEqual(run.returncode, 0, run.stdout)
            report = json.loads(run.stdout)
            self.assertEqual((report["tests"], report["passed"], report["failed"]), (10, 10, []))

    def test_no_network_llm_or_storage_reuse(self) -> None:
        src = ROOT / "apps" / "learnit-next" / "src"
        files = [src / "core" / "atlas_clock.js", src / "core" / "atlas_events.js",
                 src / "core" / "atlas_projection.js", src / "ports" / "atlas_storage.js",
                 src / "adapters" / "atlas_indexeddb.js"]
        text = "\n".join(path.read_text(encoding="utf-8") for path in files)
        for token in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource",
                      "navigator.sendBeacon", "openai", "anthropic", "gemini", "apiKey"):
            self.assertNotIn(token, text)
        storage = (src / "ports" / "atlas_storage.js").read_text(encoding="utf-8")
        self.assertIn("learnit_atlas_m1_v1", storage)
        self.assertNotIn("learnit_next_v1", storage)
        self.assertNotIn("learnit.next.v1.", storage)
        self.assertNotIn("rc718", storage.lower())

    def test_lane_scope_when_git_is_available(self) -> None:
        if not (ROOT / ".git").exists():
            self.skipTest("Git metadata unavailable")
        if subprocess.run(["git", "cat-file", "-e", f"{BASELINE}^{{commit}}"], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            self.skipTest("Exact baseline unavailable")
        out = subprocess.check_output(["git", "diff", "--name-only", f"{BASELINE}...HEAD"],
                                      cwd=ROOT, text=True, timeout=30)
        changed = {line for line in out.splitlines() if line}
        self.assertTrue(changed)
        self.assertEqual(changed - ALLOWED, set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
