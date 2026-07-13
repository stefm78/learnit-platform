/* RC698-RC701 — Objective coverage and retention protocol runtime bridge.
   It exposes truthful, machine-readable evidence without claiming learner transfer or retention. */
(function(){
  'use strict';
  AppRuntime.prototype.learningCoverageReport=function(course){
    const model=window.LearnItLearningCoverageModel;
    const target=course||this.contentStore.content;
    return model&&typeof model.courseCoverage==='function'?model.courseCoverage(target):{schema:'learnit.learning_coverage.unavailable',readyForHumanTransferProbe:false,objectives:[]};
  };
  AppRuntime.prototype.retentionProtocolReport=function(at){
    const model=window.LearnItRetentionProtocolModel;
    const protocol=this.appState.courseRetention(this.contentStore.activeCourseId);
    return model&&protocol&&typeof model.status==='function'?model.status(protocol,at):{schema:'learnit.retention_protocol.none',courseId:this.contentStore.activeCourseId,completedCount:0,dueCount:0,pendingCount:0,retentionDemonstrated:false,checkpoints:[]};
  };
  AppRuntime.prototype.recordRetentionCheckpoint=function(checkpointId,results,observedAt){
    const model=window.LearnItRetentionProtocolModel;
    const id=this.contentStore.activeCourseId;
    const protocol=this.appState.courseRetention(id);
    if(!model||!protocol||typeof model.record!=='function')return {ok:false,error:'Aucun protocole de rétention actif.'};
    try{
      const updated=model.record(protocol,checkpointId,results,observedAt||nowIso());
      this.appState.setCourseRetention(updated,id);this.appState.save();
      return {ok:true,protocol:updated,status:model.status(updated,observedAt||nowIso())};
    }catch(error){return {ok:false,error:String(error&&error.message||error)};}
  };
  if(window.__LEARNIT_TEST__){
    window.__LEARNIT_TEST__.learningCoverage=course=>runtime.learningCoverageReport(course);
    window.__LEARNIT_TEST__.retentionProtocol=at=>runtime.retentionProtocolReport(at);
    window.__LEARNIT_TEST__.recordRetention=(checkpointId,results,observedAt)=>runtime.recordRetentionCheckpoint(checkpointId,results,observedAt);
  }
})();
