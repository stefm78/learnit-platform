(function(global){
  'use strict';

  const schema='learnit.retention_protocol_model.rc701.v1';
  const CHECKPOINTS=Object.freeze([
    Object.freeze({id:'immediate',label:'Immédiat',offsetHours:0}),
    Object.freeze({id:'h72',label:'72 h',offsetHours:72}),
    Object.freeze({id:'d7',label:'7 jours',offsetHours:168})
  ]);

  function arr(value){return Array.isArray(value)?value:[];}
  function obj(value){return value&&typeof value==='object'&&!Array.isArray(value)?value:{};}
  function text(value){return String(value===undefined||value===null?'':value).trim();}
  function timestamp(value){const ms=Date.parse(text(value));return Number.isFinite(ms)?ms:NaN;}
  function iso(ms){return new Date(ms).toISOString();}
  function unique(values){const out=[];const seen=new Set();for(const value of arr(values).map(text)){if(value&&!seen.has(value)){seen.add(value);out.push(value);}}return out;}
  function clone(value){return JSON.parse(JSON.stringify(value));}
  function objectiveKey(value){return text(value).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'objectif';}

  function schedule(courseId,completedAt,objectiveKeys,transferActivityIds){
    const start=timestamp(completedAt);if(!Number.isFinite(start))throw new Error('completedAt invalide');
    const objectives=unique(objectiveKeys);const probes=unique(transferActivityIds);
    return Object.freeze({
      schema,
      protocolId:`${text(courseId)||'course'}-${start}`,
      courseId:text(courseId)||'course',
      createdAt:iso(start),
      sourceCompletedAt:iso(start),
      objectiveKeys:Object.freeze(objectives),
      transferActivityIds:Object.freeze(probes),
      checkpoints:Object.freeze(CHECKPOINTS.map(row=>Object.freeze({...row,dueAt:iso(start+row.offsetHours*3600000),status:'pending',observedAt:'',results:Object.freeze([])}))),
      claim:'Aucune rétention n’est déclarée avant observation aux échéances prévues.'
    });
  }
  function normalizeResult(row){
    const value=obj(row);return Object.freeze({objectiveKey:text(value.objectiveKey)||objectiveKey(value.objective),objective:text(value.objective),activityId:text(value.activityId),correct:value.correct===true,observedAt:text(value.observedAt),transferProbe:value.transferProbe===true,transferDistance:['near','far'].includes(text(value.transferDistance))?text(value.transferDistance):''});
  }
  function record(protocol,checkpointId,results,observedAt){
    const source=obj(protocol);const at=timestamp(observedAt);if(!Number.isFinite(at))throw new Error('observedAt invalide');
    const id=text(checkpointId);let found=false;
    const checkpoints=arr(source.checkpoints).map(row=>{
      if(text(row.id)!==id)return clone(row);found=true;
      const normalized=arr(results).map(item=>normalizeResult({...item,observedAt:iso(at)}));
      return {...clone(row),status:'completed',observedAt:iso(at),results:normalized};
    });
    if(!found)throw new Error(`checkpoint inconnu: ${id}`);
    return Object.freeze({...clone(source),checkpoints:Object.freeze(checkpoints.map(Object.freeze)),updatedAt:iso(at)});
  }
  function checkpointState(row,nowMs){
    if(text(row&&row.status)==='completed'&&text(row&&row.observedAt))return 'completed';
    const due=timestamp(row&&row.dueAt);if(!Number.isFinite(due))return 'invalid';
    if(nowMs>=due)return 'due';
    return 'pending';
  }
  function status(protocol,now){
    const current=timestamp(now===undefined?new Date().toISOString():now);if(!Number.isFinite(current))throw new Error('now invalide');
    const rows=arr(protocol&&protocol.checkpoints).map(row=>Object.freeze({...clone(row),computedStatus:checkpointState(row,current)}));
    const completed=rows.filter(row=>row.computedStatus==='completed');const due=rows.filter(row=>row.computedStatus==='due');const pending=rows.filter(row=>row.computedStatus==='pending');
    const results=completed.flatMap(row=>arr(row.results));const objectiveKeys=unique(protocol&&protocol.objectiveKeys);
    const objectiveRows=objectiveKeys.map(key=>{
      const observed=results.filter(row=>text(row.objectiveKey)===key);return Object.freeze({key,observations:observed.length,successful:observed.filter(row=>row.correct).length,checkpoints:unique(completed.filter(cp=>arr(cp.results).some(row=>text(row.objectiveKey)===key)).map(cp=>cp.id)),retained:CHECKPOINTS.every(cp=>completed.some(done=>done.id===cp.id&&arr(done.results).some(row=>text(row.objectiveKey)===key&&row.correct===true)))});
    });
    return Object.freeze({schema,protocolId:text(protocol&&protocol.protocolId),checkpoints:Object.freeze(rows),completedCount:completed.length,dueCount:due.length,pendingCount:pending.length,allObserved:completed.length===CHECKPOINTS.length,retentionDemonstrated:objectiveRows.length>0&&objectiveRows.every(row=>row.retained),objectives:Object.freeze(objectiveRows),nextDue:due[0]||pending[0]||null});
  }
  function fromAssessment(course,bilan,courseId){
    const source=obj(bilan);const activities=arr(course&&course.activities);const byId=new Map(activities.map(activity=>[text(activity&&activity.id),activity]));
    const transferRows=arr(source.assessmentEvidence).filter(row=>{const activity=byId.get(text(row&&row.id));return !!(activity&&activity.transfer_probe===true);});
    if(text(source.mode)!=='validation'||!transferRows.length)return null;
    let protocol=schedule(courseId||course&&course.id||course&&course.title,source.completedAt||new Date().toISOString(),transferRows.map(row=>text(row&&row.objectiveKey)||objectiveKey(row&&row.objective)),transferRows.map(row=>text(row&&row.id)));
    protocol=record(protocol,'immediate',transferRows.map(row=>{const activity=byId.get(text(row&&row.id))||{};return {objectiveKey:text(row&&row.objectiveKey)||objectiveKey(row&&row.objective),objective:text(row&&row.objective),activityId:text(row&&row.id),correct:row&&row.correct===true,transferProbe:true,transferDistance:text(activity.transfer_distance)};}),source.completedAt||new Date().toISOString());
    return protocol;
  }
  function merge(existing,next){
    if(!existing)return next;if(!next)return existing;
    if(text(existing.protocolId)===text(next.protocolId))return existing;
    return next;
  }
  function audit(){
    const course={id:'c',activities:[{id:'t1',objective:'Transférer',transfer_probe:true,transfer_distance:'far'}]};
    const completedAt='2026-01-01T00:00:00Z';
    const bilan={mode:'validation',completedAt,assessmentEvidence:[{id:'t1',objective:'Transférer',objectiveKey:'transferer',correct:true}]};
    let protocol=fromAssessment(course,bilan,'c');
    const at72=status(protocol,'2026-01-04T00:00:00Z');
    protocol=record(protocol,'h72',[{objectiveKey:'transferer',activityId:'t1',correct:true,transferProbe:true,transferDistance:'far'}],'2026-01-04T00:00:00Z');
    protocol=record(protocol,'d7',[{objectiveKey:'transferer',activityId:'t1',correct:true,transferProbe:true,transferDistance:'far'}],'2026-01-08T00:00:00Z');
    const final=status(protocol,'2026-01-08T00:00:01Z');
    return {schema,ok:at72.completedCount===1&&at72.dueCount===1&&!at72.retentionDemonstrated&&final.allObserved&&final.retentionDemonstrated,at72,final};
  }

  const api=Object.freeze({schema,CHECKPOINTS,objectiveKey,schedule,record,status,fromAssessment,merge,audit});
  global.LearnItRetentionProtocolModel=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
