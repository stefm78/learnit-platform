#!/usr/bin/env python3
import pathlib
import subprocess
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

NODE = r'''
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const ROOT=process.argv[1];
const mod=async p=>import(pathToFileURL(path.join(ROOT,p)).href);
const A=await mod('src/core/activity_semantics.js');
const C=await mod('src/core/contract.js');
const I=await mod('src/core/import.js');
const P=await mod('src/core/progress.js');
const S=await mod('src/core/session.js');
const X=await mod('src/integration/atlas/activity_projection.js');
const fixture=JSON.parse(fs.readFileSync(path.join(ROOT,'tests/fixtures/student_v01_v4_runtime.json'),'utf8'));
const clone=v=>structuredClone(v);
let n=0;
const ok=(value,message)=>{assert.ok(value,message);n+=1};
const eq=(a,b,message)=>{assert.deepEqual(a,b,message);n+=1};
const bad=(fn,re)=>{assert.throws(fn,re);n+=1};

async function rehash(pkg){
  for(const course of pkg.courses){
    for(const activity of course.activities){
      activity.activityRevisionDigest=await C.sha256Canonical(activity,{omitRootKey:'activityRevisionDigest'});
    }
    course.courseRevisionDigest=await C.sha256Canonical(course,{omitRootKey:'courseRevisionDigest'});
  }
  pkg.packageRevisionDigest=await C.sha256Canonical(pkg,{omitRootKey:'packageRevisionDigest'});
  return pkg;
}

const historicalV2={
  contract:'learnit.kit.v2',
  packageLineageId:'11111111-1111-4111-8111-111111111111',
  packageRevisionId:'11111111-1111-4111-8111-111111111112',
  packageRevisionDigest:'sha256:0eee635695f7adfe55d0c31d126019127d99ebae3ead4750cdcafddb13c594c6',
  title:'Fixture QA minimale QCM et fill',
  description:'Fixture indépendante destinée aux tests contradictoires du contrat v2.',
  versionLabel:'qa-v1', language:'fr-FR', courses:[{
    courseLineageId:'22222222-2222-4222-8222-222222222221',
    courseRevisionId:'22222222-2222-4222-8222-222222222222',
    courseRevisionDigest:'sha256:e61ebf045d9de347fcb8422692f384f40cec2879000ba187dc4b6ceb57b650a7',
    title:'Boucle minimale de validation',
    subtitle:'Identités stables, QCM par choiceId et token fill réutilisable.',
    estimatedMinutes:8,
    objectives:[
      {objectiveId:'33333333-3333-4333-8333-333333333331',label:'Valider une réponse QCM par identifiant.'},
      {objectiveId:'33333333-3333-4333-8333-333333333332',label:'Réutiliser un token fill dans la limite de maxUses.'},
    ],
    activities:[{
      activityLineageId:'44444444-4444-4444-8444-444444444441',
      activityRevisionId:'44444444-4444-4444-8444-444444444442',
      activityRevisionDigest:'sha256:ce2098a44f788970d45c8c82eb0270b697c080634895154c2c0d39824be5129d',
      objectiveIds:['33333333-3333-4333-8333-333333333331'],type:'qcm',
      prompt:'Quelle propriété garantit que réordonner les choix ne change pas la correction ?',
      explanation:'La correction référence le choiceId, jamais la position dans le tableau.',difficulty:'easy',learningPhase:'comprehension',assessmentRole:'practice',
      choices:[
        {choiceId:'55555555-5555-4555-8555-555555555551',label:'Le texte du premier choix'},
        {choiceId:'55555555-5555-4555-8555-555555555552',label:'Le choiceId explicitement référencé'},
        {choiceId:'55555555-5555-4555-8555-555555555553',label:'La position du choix dans le tableau'},
      ],correctChoiceId:'55555555-5555-4555-8555-555555555552',
    },{
      activityLineageId:'66666666-6666-4666-8666-666666666661',
      activityRevisionId:'66666666-6666-4666-8666-666666666662',
      activityRevisionDigest:'sha256:6524564f774179d05708bf1eca53b6c334992ead8e82512e5d70f5bd0c911bca',
      objectiveIds:['33333333-3333-4333-8333-333333333332'],type:'fill',
      prompt:'Compléter la phrase avec le même token aux deux positions.',
      explanation:'Le token « réutilisable » déclare maxUses=2 et peut donc remplir deux slots distincts.',difficulty:'medium',learningPhase:'application',assessmentRole:'validation',
      segments:[{text:'Un token '},{slotId:'77777777-7777-4777-8777-777777777771'},{text:' reste disponible pour un second slot lorsqu’il est déclaré '},{slotId:'77777777-7777-4777-8777-777777777772'},{text:'.'}],
      tokens:[{tokenId:'88888888-8888-4888-8888-888888888881',label:'réutilisable',maxUses:2},{tokenId:'88888888-8888-4888-8888-888888888882',label:'à usage unique',maxUses:1}],
      answers:[{slotId:'77777777-7777-4777-8777-777777777771',tokenId:'88888888-8888-4888-8888-888888888881'},{slotId:'77777777-7777-4777-8777-777777777772',tokenId:'88888888-8888-4888-8888-888888888881'}],
    }],
  }],
};

// Exact v2 regression fixture: old canonical digests remain accepted unchanged.
let r=await C.validatePackageObject(historicalV2); ok(r.ok,JSON.stringify(r.errors));
const v2q=historicalV2.courses[0].activities[0], v2f=historicalV2.courses[0].activities[1];
eq(A.evaluateActivityResponse(v2q,{choiceId:v2q.correctChoiceId}).correct,true);
eq(A.evaluateActivityResponse(v2q,{choiceId:v2q.choices[0].choiceId}).correct,false);
eq(A.evaluateActivityResponse(v2f,Object.fromEntries(v2f.answers.map(x=>[x.slotId,x.tokenId]))).correct,true);

// v3 constructed semantics are explicit, canonical-text-match-v1 and case-sensitive.
const v3={contract:'learnit.kit.v3',packageLineageId:'90000001-0001-4001-8001-000000000001',packageRevisionId:'90000002-0002-4002-8002-000000000002',packageRevisionDigest:'sha256:'+'0'.repeat(64),title:'v3',versionLabel:'v3',language:'fr-FR',courses:[{courseLineageId:'90000003-0003-4003-8003-000000000003',courseRevisionId:'90000004-0004-4004-8004-000000000004',courseRevisionDigest:'sha256:'+'0'.repeat(64),title:'c',estimatedMinutes:2,objectives:[{objectiveId:'90000005-0005-4005-8005-000000000005',label:'o'}],activities:[{activityLineageId:'90000006-0006-4006-8006-000000000006',activityRevisionId:'90000007-0007-4007-8007-000000000007',activityRevisionDigest:'sha256:'+'0'.repeat(64),objectiveIds:['90000005-0005-4005-8005-000000000005'],type:'constructed',prompt:'p',explanation:'e',difficulty:'easy',learningPhase:'application',assessmentRole:'practice',acceptedResponses:['Réponse exacte']}]}]};
await rehash(v3); r=await C.validatePackageObject(v3); ok(r.ok,JSON.stringify(r.errors));
const cons=v3.courses[0].activities[0];
eq(A.evaluateActivityResponse(cons,{text:'  Re\u0301ponse\t exacte  '}).correct,true);
eq(A.evaluateActivityResponse(cons,{text:'réponse exacte'}).correct,false);
bad(()=>A.evaluateActivityResponse(cons,{text:' \t\n '}),/blank/i);

// v4 contract and discriminator admission.
r=await C.validatePackageObject(fixture); ok(r.ok,JSON.stringify(r.errors));
const unknownContract=clone(fixture); unknownContract.contract='learnit.kit.v5'; r=await C.validatePackageObject(unknownContract); ok(!r.ok && r.errors.some(x=>x.code==='unsupported_contract'));
const unknownType=clone(fixture); unknownType.courses[0].activities[0].type='essay'; await rehash(unknownType); r=await C.validatePackageObject(unknownType); ok(!r.ok && r.errors.some(x=>x.code==='activity_type'));

const byType=Object.fromEntries(fixture.courses[0].activities.map(x=>[x.type,x]));
// Matching positive and duplicate/unknown/omission/extra attacks.
const m=byType.matching, ma={associations:m.matches.map(x=>({...x}))};
eq(A.evaluateActivityResponse(m,ma).correct,true);
bad(()=>A.evaluateActivityResponse(m,{associations:[ma.associations[0],ma.associations[0]]}),/duplicate|multi-use/i);
bad(()=>A.evaluateActivityResponse(m,{associations:[{leftItemId:'ffffffff-ffff-4fff-8fff-ffffffffffff',rightItemId:m.rightItems[0].itemId},ma.associations[1]]}),/unknown left/i);
bad(()=>A.evaluateActivityResponse(m,{associations:ma.associations.slice(0,1)}),/cover every|omit|incomplete/i);
bad(()=>A.evaluateActivityResponse(m,{associations:[...ma.associations,{...ma.associations[0]}]}),/cover every|incomplete/i);
// Order positive and attacks.
const o=byType.order;
eq(A.evaluateActivityResponse(o,{orderedItemIds:[...o.correctOrder]}).correct,true);
bad(()=>A.evaluateActivityResponse(o,{orderedItemIds:[o.items[0].itemId,o.items[0].itemId,o.items[2].itemId]}),/duplicate/i);
bad(()=>A.evaluateActivityResponse(o,{orderedItemIds:[o.items[0].itemId,o.items[1].itemId,'ffffffff-ffff-4fff-8fff-ffffffffffff']}),/unknown/i);
bad(()=>A.evaluateActivityResponse(o,{orderedItemIds:o.correctOrder.slice(0,2)}),/every authored|incomplete/i);
// Classify positive and duplicate/unknown/multi-bucket/omission attacks.
const cl=byType.classify;
eq(A.evaluateActivityResponse(cl,{assignments:cl.assignments.map(x=>({...x}))}).correct,true);
bad(()=>A.evaluateActivityResponse(cl,{assignments:[cl.assignments[0],{itemId:cl.assignments[0].itemId,bucketId:cl.buckets[0].bucketId}]}),/more than once|multiple/i);
bad(()=>A.evaluateActivityResponse(cl,{assignments:[{itemId:'ffffffff-ffff-4fff-8fff-ffffffffffff',bucketId:cl.buckets[0].bucketId},cl.assignments[1]]}),/unknown classify item/i);
bad(()=>A.evaluateActivityResponse(cl,{assignments:[{itemId:cl.items[0].itemId,bucketId:'ffffffff-ffff-4fff-8fff-ffffffffffff'},cl.assignments[1]]}),/unknown bucket/i);
bad(()=>A.evaluateActivityResponse(cl,{assignments:cl.assignments.slice(0,1)}),/every authored|incomplete/i);

// Non-scored response semantics.
const le=A.evaluateActivityResponse(byType.lesson,{acknowledged:true}); eq(le.scored,false); ok(!Object.hasOwn(le,'correct'));
const fl=A.evaluateActivityResponse(byType.flashcard,{revealed:true}); eq(fl.scored,false); ok(!Object.hasOwn(fl,'correct'));
bad(()=>A.evaluateActivityResponse(byType.lesson,{acknowledged:false}),/acknowledged/i);
bad(()=>A.evaluateActivityResponse(byType.flashcard,{revealed:false}),/revealed/i);

// Exact learner-safe projection and secret stripping for every scored type.
const forbidden={qcm:['correctChoiceId'],fill:['answers'],constructed:['acceptedResponses'],matching:['matches'],order:['correctOrder'],classify:['assignments']};
for(const type of Object.keys(forbidden)){
  const p=X.projectActivityPresentation(byType[type],{assets:fixture.assets});
  const serialized=JSON.stringify(p);
  for(const secret of forbidden[type]) ok(!serialized.includes(`"${secret}"`),`${type} leaked ${secret}`);
  ok(Array.isArray(p.media));
}
const mp=X.projectActivityPresentation(m,{assets:fixture.assets});
eq(mp.rightItems.map(x=>x.itemId),[m.rightItems[1].itemId,m.rightItems[0].itemId]);
const cp=X.projectActivityPresentation(byType.constructed,{assets:fixture.assets});
eq(cp.media[0],{assetId:fixture.assets[0].assetId,format:'svg',alt:'Schéma pédagogique',caption:'Exemple sûr',pedagogicalRole:'question_stimulus',data:fixture.assets[0].data,placement:'prompt',display:'contained',zoomable:false});

// Media references and unsafe SVG fail closed at runtime/import admission.
const unsafe=clone(fixture); unsafe.assets[0].data='<svg onload="alert(1)"><script>alert(1)</script></svg>'; await rehash(unsafe); r=await C.validatePackageObject(unsafe); ok(!r.ok && r.errors.some(x=>x.code==='unsafe_svg'));
const missingMedia=clone(fixture); missingMedia.courses[0].activities.find(x=>x.type==='constructed').media[0].assetId='ffffffff-ffff-4fff-8fff-ffffffffffff'; await rehash(missingMedia); r=await C.validatePackageObject(missingMedia); ok(!r.ok && r.errors.some(x=>x.code==='missing_asset_reference'));
const raster=clone(fixture); raster.assets.push({assetId:'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',type:'image',format:'png',alt:'Raster',pedagogicalRole:'memory_anchor',data:'data:image/png;base64,iVBORw0KGgo='}); await rehash(raster); r=await C.validatePackageObject(raster); ok(r.ok,JSON.stringify(r.errors));
const remoteRaster=clone(raster); remoteRaster.assets.at(-1).data='https://example.invalid/x.png'; await rehash(remoteRaster); r=await C.validatePackageObject(remoteRaster); ok(!r.ok && r.errors.some(x=>x.code==='unsafe_media'));

// Import admission is explicit for v2/v3/v4 and rejects anything else without migration.
class ImportStore { constructor(){this.revisions=new Map();this.imported=[]} async getRevisionDigestIndex(){return new Map(this.revisions)} async commitImport(plan){this.imported.push(plan)} }
const importStore=new ImportStore(), imports=I.createImportService(importStore);
ok((await imports.validatePackage(historicalV2)).ok);
ok((await imports.validatePackage(v3)).ok);
ok((await imports.validatePackage(fixture)).ok);
ok(!(await imports.validatePackage({...fixture,contract:'legacy'})).ok);

// Session traversal/resume with non-scored completion while mastery/review counters stay untouched.
class MemoryStore {
  constructor(courseRecord){this.courseRecord=courseRecord;this.progress=new Map();this.meta=new Map();this.objectives=[]}
  async getCourse(id){return id===this.courseRecord.courseInstallId?structuredClone(this.courseRecord):null}
  async listProgress(id){return [...this.progress.values()].filter(x=>x.courseInstallId===id).map(value=>structuredClone(value))}
  async getProgress(id,rev){return this.progress.has(`${id}:${rev}`)?structuredClone(this.progress.get(`${id}:${rev}`)):null}
  async putProgress(record){this.progress.set(`${record.courseInstallId}:${record.activityRevisionId}`,structuredClone(record))}
  async getMeta(k){return this.meta.has(k)?structuredClone(this.meta.get(k)):null}
  async setMeta(k,v){this.meta.set(k,structuredClone(v))}
  async deleteMeta(k){this.meta.delete(k)}
  async listObjectiveProgress(){return this.objectives.map(value=>structuredClone(value))}
  async putObjectiveProgressRecords(records){this.objectives=records.map(value=>structuredClone(value))}
}
const course=clone(fixture.courses[0]);
course.activities=[clone(byType.lesson),clone(byType.flashcard),clone(byType.matching)];
const record={courseInstallId:'course-1',displayLabel:'Runtime',title:'Runtime',course};
const mem=new MemoryStore(record);
const captured=[];
const objectiveModule={
  reduceObjectiveEvents(objectiveId,events){captured.push(events.map(e=>({...e})));const train=events.filter(e=>e.type==='training-result'),val=events.filter(e=>e.type==='validation-result');return {objectiveId,trainingAttempts:train.length,latestTrainingCorrect:train.length?train.at(-1).correct:null,needsReview:train.length?train.at(-1).correct===false:false,validationAttempts:val.length,latestValidationCorrect:val.length?val.at(-1).correct:null,status:events.length?'training':'not-started'}},
  normalizeObjectiveProgress(x){return x},
};
const recommendationModule={recommendNextObjective(){return null}};
const integrations=P.createLearningLoopV2DomainAdapters(objectiveModule,recommendationModule);
const progress=P.createProgressService(mem,integrations);
let sessions=S.createSessionService(mem,progress);
let current=await sessions.startCourse('course-1'); eq(current.currentActivity.type,'lesson');
let result=await sessions.answer(current.currentActivity.activityRevisionId,{acknowledged:true}); eq(result.scored,false); eq(result.nextActivity.type,'flashcard');
let records=await mem.listProgress('course-1'); eq(records.length,1); eq(records[0].scored,false); ok(!Object.hasOwn(records[0],'correct')); eq(progress.reviewQueue(course,records).length,0); eq((await progress.getObjectiveProgress('course-1',course)).objectives[0].trainingAttempts,0); eq((await progress.getObjectiveProgress('course-1',course)).objectives[0].validationAttempts,0);
sessions.clearActiveSession(); sessions=S.createSessionService(mem,progress); current=await sessions.resumeActiveCourse(); eq(current.currentActivity.type,'flashcard');
result=await sessions.answer(current.currentActivity.activityRevisionId,{revealed:true}); eq(result.scored,false); eq(result.nextActivity.type,'matching');
records=await mem.listProgress('course-1'); eq(records.length,2); ok(records.every(x=>x.scored===false&&!Object.hasOwn(x,'correct'))); eq(progress.reviewQueue(course,records).length,0); const beforeScore=await progress.getObjectiveProgress('course-1',course); eq(beforeScore.objectives[0].status,'not-started'); eq(beforeScore.objectives[0].trainingAttempts,0);
result=await sessions.answer(result.nextActivity.activityRevisionId,{associations:byType.matching.matches.map(x=>({...x}))}); eq(result.scored,true); eq(result.correct,true); const afterScore=await progress.getObjectiveProgress('course-1',course); eq(afterScore.objectives[0].trainingAttempts,1);
ok(captured.filter(events=>events.length>0).every(events=>events.every(e=>e.type==='training-result'||e.type==='validation-result')));

console.log(`STUDENT_V01_LEARNING_RUNTIME_PASS ${n}/${n}`);
'''

class StudentV01LearningRuntime(unittest.TestCase):
    def test_runtime_semantics(self):
        proc = subprocess.run(
            ['node', '--experimental-default-type=module', '--input-type=module', '-e', textwrap.dedent(NODE), str(ROOT)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('STUDENT_V01_LEARNING_RUNTIME_PASS', proc.stdout)
        print(proc.stdout.strip())

    def test_scope_files_are_syntax_valid(self):
        paths = [
            ROOT/'src/core/activity_semantics.js',
            ROOT/'src/core/contract.js',
            ROOT/'src/core/import.js',
            ROOT/'src/core/session.js',
            ROOT/'src/core/progress.js',
            ROOT/'src/integration/atlas/activity_projection.js',
            ROOT/'src/integration/atlas/import_adapter.js',
        ]
        for source in paths:
            proc = subprocess.run(['node', '--check', str(source)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f'{source}: {proc.stderr}')

if __name__ == '__main__':
    unittest.main(verbosity=2)
