(function(){
  'use strict';

  const SCHEMA='learnit.pedagogical_variety.v1';
  const NEAR_DUPLICATE_THRESHOLD=0.82;
  const ADJACENT_REPETITION_THRESHOLD=0.70;
  const MAX_LOOKAHEAD=8;
  const STOP=new Set('a au aux avec ce ces dans de des du elle en et est il la le les leur lui ma mais mes mon ne nos notre nous on ou par pas pour que qui sa se ses son sur ta te tes ton tu un une vos votre vous'.split(' '));

  function arr(v){return Array.isArray(v)?v:[];}
  function text(v){return String(v===undefined||v===null?'':v).trim();}
  function normalize(value){
    return text(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim().replace(/\s+/g,' ');
  }
  function tokens(value){return normalize(value).split(' ').filter(word=>word.length>1&&!STOP.has(word));}
  function uniq(values){return [...new Set(arr(values).map(text).filter(Boolean))];}
  function tokenSet(value){return new Set(tokens(value));}
  function jaccard(a,b){
    const A=a instanceof Set?a:tokenSet(a), B=b instanceof Set?b:tokenSet(b);
    if(!A.size&&!B.size)return 0;
    if(!A.size||!B.size)return 0;
    let common=0;for(const item of A)if(B.has(item))common++;
    return common/(A.size+B.size-common);
  }
  function answerText(activity){
    const a=activity||{};
    if(a.type==='qcm')return arr(a.choices).join(' ');
    if(a.type==='matching')return arr(a.pairs).flat().join(' ');
    if(a.type==='order'||a.type==='fill')return arr(a.answer).join(' ');
    return text(a.answer||a.back);
  }
  function profile(activity){
    const a=activity||{};
    const prompt=text(a.question||a.front||a.prompt);
    const objective=text(a.objective);
    return {
      id:text(a.id),type:text(a.type),objective,objectiveKey:normalize(objective),
      prompt,promptKey:normalize(prompt),promptTokens:tokenSet(prompt),
      answerKey:normalize(answerText(a)),phase:text(a.learning_phase),
      role:text(a.assessment_role),difficulty:text(a.difficulty),
      commonErrors:uniq(a.common_errors).map(normalize).filter(Boolean)
    };
  }
  function overlapCount(a,b){const B=new Set(arr(b));return arr(a).filter(item=>B.has(item)).length;}
  function similarity(left,right){
    const a=left&&left.promptTokens?left:profile(left), b=right&&right.promptTokens?right:profile(right);
    if(a.id&&b.id&&a.id===b.id)return 1;
    if(a.promptKey&&a.promptKey===b.promptKey)return 1;
    const prompt=jaccard(a.promptTokens,b.promptTokens);
    const objective=a.objectiveKey&&a.objectiveKey===b.objectiveKey?1:jaccard(a.objectiveKey,b.objectiveKey);
    const answer=a.answerKey&&b.answerKey?jaccard(a.answerKey,b.answerKey):0;
    const errorOverlap=Math.min(1,overlapCount(a.commonErrors,b.commonErrors)/Math.max(1,Math.min(a.commonErrors.length||1,b.commonErrors.length||1)));
    return Math.max(0,Math.min(1,prompt*0.62+objective*0.23+answer*0.10+errorOverlap*0.05));
  }
  function isNearDuplicate(a,b,threshold=NEAR_DUPLICATE_THRESHOLD){return similarity(a,b)>=Number(threshold||NEAR_DUPLICATE_THRESHOLD);}
  function isMeaningfullyDifferent(a,b){
    const pa=profile(a), pb=profile(b), sim=similarity(pa,pb);
    return pa.type!==pb.type?sim<0.90:sim<0.72;
  }
  function stableHash(value){let h=2166136261;for(const ch of text(value)){h^=ch.charCodeAt(0);h=Math.imul(h,16777619);}return h>>>0;}
  function pairPenalty(previous,candidate,beforePrevious){
    const a=profile(previous), b=profile(candidate), c=beforePrevious?profile(beforePrevious):null;
    const sim=similarity(a,b);
    let value=sim*100;
    if(a.objectiveKey&&a.objectiveKey===b.objectiveKey)value+=24;
    if(a.type&&a.type===b.type)value+=10;
    if(a.phase&&a.phase===b.phase)value+=3;
    if(c&&c.type===a.type&&a.type===b.type)value+=26;
    return value;
  }
  function adjacentMetrics(activities,ids){
    const byId=new Map(arr(activities).map(a=>[text(a.id),a]));
    const pairs=[];
    for(let i=1;i<arr(ids).length;i++){
      const a=byId.get(ids[i-1]), b=byId.get(ids[i]);if(!a||!b)continue;
      const sim=similarity(a,b);const pa=profile(a),pb=profile(b);
      const repeated=sim>=ADJACENT_REPETITION_THRESHOLD||(pa.type===pb.type&&pa.objectiveKey&&pa.objectiveKey===pb.objectiveKey);
      pairs.push({left:ids[i-1],right:ids[i],similarity:Number(sim.toFixed(3)),repeated});
    }
    const repeated=pairs.filter(row=>row.repeated).length;
    return {pairs,repeated,total:pairs.length,rate:pairs.length?Number((repeated/pairs.length).toFixed(3)):0,maxSimilarity:pairs.length?Math.max(...pairs.map(row=>row.similarity)):0};
  }
  function sequenceIds(course,ids,options={}){
    const activities=arr(course&&course.activities), byId=new Map(activities.map(a=>[text(a.id),a]));
    const seen=new Set(), queue=[];let dropped=0;
    for(const raw of arr(ids)){const id=text(raw);if(!id||!byId.has(id))continue;if(seen.has(id)){dropped++;continue;}seen.add(id);queue.push(id);}
    const original=[...queue], seed=text(options.seed||'stable'), mode=text(options.mode||'normal')||'normal';
    const preserveFirst=options.preserveFirst!==false, swaps=[];
    for(let i=preserveFirst?1:0;i<queue.length;i++){
      const prev=i>0?byId.get(queue[i-1]):null, prev2=i>1?byId.get(queue[i-2]):null;
      if(!prev)continue;
      const current=byId.get(queue[i]);let best=i,bestPenalty=pairPenalty(prev,current,prev2)+(mode==='normal'?0:stableHash(seed+'|'+queue[i])%5/100);
      const end=Math.min(queue.length,i+MAX_LOOKAHEAD+1);
      for(let j=i+1;j<end;j++){
        const candidate=byId.get(queue[j]);
        const displacement=(j-i)*(mode==='normal'?3.5:0.75);
        const tie=(stableHash(seed+'|'+queue[j])%1000)/100000;
        const penalty=pairPenalty(prev,candidate,prev2)+displacement+tie;
        if(penalty+2<bestPenalty){best=j;bestPenalty=penalty;}
      }
      if(best!==i){const moved=queue[best];queue.splice(best,1);queue.splice(i,0,moved);swaps.push({at:i,from:best,id:moved});}
    }
    const before=adjacentMetrics(activities,original), after=adjacentMetrics(activities,queue);
    return {schema:SCHEMA,queue,original,mode,seed,droppedDuplicateIds:dropped,swaps,before,after,improved:after.repeated<=before.repeated,deterministic:true,preservesMembership:queue.length===original.length&&queue.every(id=>seen.has(id))};
  }
  function auditCourse(course,options={}){
    const activities=arr(course&&course.activities), rows=activities.map(profile), exact=[],near=[];
    const ids=new Set(),duplicateIds=[];
    for(const row of rows){if(ids.has(row.id))duplicateIds.push(row.id);ids.add(row.id);}
    for(let i=0;i<activities.length;i++)for(let j=i+1;j<activities.length;j++){
      const a=rows[i],b=rows[j],score=similarity(a,b);
      if(a.promptKey&&a.promptKey===b.promptKey)exact.push({left:a.id,right:b.id,score:1});
      else if(score>=Number(options.threshold||NEAR_DUPLICATE_THRESHOLD))near.push({left:a.id,right:b.id,score:Number(score.toFixed(3)),sameType:a.type===b.type,sameObjective:!!a.objectiveKey&&a.objectiveKey===b.objectiveKey});
    }
    const objectiveGroups={};for(const row of rows){if(!row.objectiveKey)continue;(objectiveGroups[row.objectiveKey]||(objectiveGroups[row.objectiveKey]=[])).push(row);}
    const weakVariants=[];for(const group of Object.values(objectiveGroups))if(group.length>1){const types=new Set(group.map(row=>row.type));const max=Math.max(...group.flatMap((a,i)=>group.slice(i+1).map(b=>similarity(a,b))),0);if(types.size===1&&max>=0.72)weakVariants.push({objective:group[0].objective,ids:group.map(row=>row.id),types:[...types],maxSimilarity:Number(max.toFixed(3))});}
    return {schema:SCHEMA,ok:duplicateIds.length===0&&exact.length===0,activityCount:activities.length,duplicateIds:uniq(duplicateIds),exactDuplicates:exact,nearDuplicates:near,weakVariants,warningCount:near.length+weakVariants.length,summary:exact.length?`${exact.length} doublon(s) exact(s)`:near.length?`${near.length} formulation(s) très proche(s)`:'Variété satisfaisante'};
  }
  function selfTest(){
    const course={activities:[
      {id:'a',type:'qcm',objective:'Calculer la tension',question:'Quelle tension obtient-on avec U égale R fois I ?',choices:['six volts','trois volts'],answer:0,learning_phase:'application'},
      {id:'b',type:'qcm',objective:'Calculer la tension',question:'Quelle tension obtient-on ici avec U égale R fois I ?',choices:['six volts','trois volts'],answer:0,learning_phase:'application'},
      {id:'c',type:'order',objective:'Calculer la tension',question:'Ordonne les étapes pour appliquer la loi d Ohm.',answer:['formule','calcul'],learning_phase:'remediation'},
      {id:'d',type:'flashcard',objective:'Identifier une unité',question:'Quelle est l unité de la tension ?',answer:'volt',learning_phase:'activation'}
    ]};
    const audit=auditCourse(course);const one=sequenceIds(course,['a','b','c','d'],{seed:'x',mode:'review'});const two=sequenceIds(course,['a','b','c','d'],{seed:'x',mode:'review'});
    return {ok:audit.nearDuplicates.length>=1&&isMeaningfullyDifferent(course.activities[0],course.activities[2])&&one.after.repeated<=one.before.repeated&&JSON.stringify(one.queue)===JSON.stringify(two.queue)&&one.preservesMembership,audit,plan:one};
  }

  window.LearnItVarietyModel=Object.freeze({SCHEMA,NEAR_DUPLICATE_THRESHOLD,ADJACENT_REPETITION_THRESHOLD,normalize,profile,similarity,isNearDuplicate,isMeaningfullyDifferent,sequenceIds,auditCourse,adjacentMetrics,selfTest});
})();
