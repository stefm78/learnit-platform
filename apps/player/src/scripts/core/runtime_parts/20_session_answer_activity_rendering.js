    class SessionController{
      constructor(appState,journal,contentStore){this.appState=appState;this.journal=journal;this.contentStore=contentStore;}
      get session(){return this.appState.state.session;}
      activityIds(){return this.contentStore.content.activities.map(a=>a.id);}
      queue(){return Array.isArray(this.session.queue)&&this.session.queue.length?this.session.queue:this.activityIds();}
      get total(){return this.queue().length;}
      modePolicy(modeOrSession=this.session){const model=window.LearnItSessionModeModel;return model&&typeof model.sessionPolicy==='function'?model.sessionPolicy(modeOrSession):{id:(modeOrSession&&modeOrSession.mode)||modeOrSession||'training',label:'Entraînement',detail:'Progresser',feedbackTiming:'immediate',allowRetry:true,showHints:true,recordProgress:true};}
      newVarietySeed(mode){return this.contentStore.content.contentVersion+'|'+mode+'|'+nowIso()+'|'+Math.random().toString(36).slice(2);}
      prepareQueue(ids,mode,seed){const valid=this.activityIds();const requested=(ids||[]).filter(id=>valid.includes(id));const model=window.LearnItVarietyModel;const policy=this.modePolicy(mode);const result=model&&typeof model.sequenceIds==='function'?model.sequenceIds(this.contentStore.content,requested,{mode:policy.id,seed,preserveFirst:true}):{queue:requested,swaps:[],before:{repeated:0},after:{repeated:0},deterministic:false};return {queue:result.queue,varietySeed:seed,varietyPlan:{schema:result.schema||'learnit.pedagogical_variety.fallback',swaps:result.swaps||[],before:result.before||{},after:result.after||{},droppedDuplicateIds:Number(result.droppedDuplicateIds||0),deterministic:!!result.deterministic}};}
      baseSession(mode,ids,extra={}){const policy=this.modePolicy(mode);const seed=this.newVarietySeed(policy.id);const plan=this.prepareQueue(ids,policy.id,seed);return {status:'active',mode,modePolicy:policy,currentIndex:0,queue:plan.queue,answers:{},contentVersion:this.contentStore.content.contentVersion,retryNonceByActivity:{},shuffleSeed:seed,varietySeed:seed,varietyPlan:plan.varietyPlan,...extra};}
      start(){return this.startMode('training');}
      startMode(mode,meta={}){const model=window.LearnItSessionModeModel;const progress=this.appState.courseProgress(this.contentStore.activeCourseId);const plan=model&&typeof model.buildPlan==='function'?model.buildPlan(this.contentStore.content,progress,mode,meta):{ok:true,mode:mode||'training',queue:this.activityIds(),policy:this.modePolicy(mode),summary:'Séance'};if(!plan.ok||!plan.queue.length){this.appState.state.session=this.baseSession('training',this.activityIds(),{modePlan:{...plan,fallback:true}});}else{this.appState.state.session=this.baseSession(plan.mode,plan.queue,{modePlan:plan,modePolicy:plan.policy||this.modePolicy(plan.mode)});}this.appState.save();this.journal.record('start_mode_session',this.snapshot());return plan;}
      startReview(ids){const valid=this.activityIds();const queue=(ids||[]).filter(id=>valid.includes(id));if(!queue.length){this.startMode('review');return;}this.appState.state.session=this.baseSession('review',queue);this.appState.save();this.journal.record('start_review_session',this.snapshot());}
      startTargetedReview(ids,meta={}){const valid=this.activityIds();const queue=(ids||[]).filter(id=>valid.includes(id));if(!queue.length){this.start();return;}const remediation={summary:meta.summary||'Reprise ciblée',focus:meta.focus||'',objectives:meta.objectives||[],hints:meta.hints||[],typeCounts:meta.typeCounts||{},metadataCoverage:meta.metadataCoverage||0,queueLength:queue.length,reasons:meta.reasons||[],maxRounds:Number(meta.maxRounds||2),exhausted:meta.exhausted||[],source:meta.source||'progress-evidence',createdAt:nowIso()};this.appState.state.session=this.baseSession('targeted-review',queue,{remediation});this.appState.save();this.journal.record('start_targeted_review_session',this.snapshot());}
      startSpacedReview(ids,meta={}){const valid=this.activityIds();const queue=(ids||[]).filter(id=>valid.includes(id));if(!queue.length){this.start();return;}const reviewPlan={summary:meta.summary||'Révision espacée',focus:meta.focus||'Consolidation',rows:meta.rows||[],queueLength:queue.length,totalDue:Number(meta.totalDue||queue.length),deferredCount:Number(meta.deferredCount||0),maxItems:Number(meta.maxItems||queue.length),source:meta.source||'spaced-review-v1',createdAt:nowIso()};this.appState.state.session=this.baseSession('spaced-review',queue,{reviewPlan});this.appState.save();this.journal.record('start_spaced_review_session',this.snapshot());}
      resume(){if(this.session.status!=='active')this.start();else this.journal.record('resume_session',this.snapshot());}
      quit(){if(this.session.status==='active')this.journal.record('quit_session',this.snapshot());this.appState.save();}
      newAfterComplete(){this.start();}
      currentActivity(){const id=this.queue()[this.session.currentIndex];return this.contentStore.content.activities.find(a=>a.id===id)||this.contentStore.content.activities[0];}
      saveAnswer(result){const a=this.currentActivity();const at=nowIso();const policy=this.modePolicy();this.session.answers[a.id]={correct:!!result.correct,expected:result.expected,at,mode:this.session.mode||policy.id,policyId:policy.id};if(policy.recordProgress!==false)this.appState.recordActivityProgress(a.id,result,a,{mode:this.session.mode||policy.id,maxRounds:this.session.remediation&&this.session.remediation.maxRounds,at});this.appState.save();this.journal.record('answer_validated',{activityId:a.id,correct:!!result.correct,position:this.session.currentIndex+1,total:this.total,mode:this.session.mode||policy.id,policyId:policy.id,deferred:policy.feedbackTiming==='deferred'});}
      moveNext(){
        const policy=this.modePolicy();
        if(this.session.currentIndex>=this.total-1){
          this.session.status='completed';
          if(policy.recordProgress!==false)this.appState.mergeSessionIntoProgress();
          const completed=this.summary();
          const retentionModel=window.LearnItRetentionProtocolModel;
          if(retentionModel&&typeof retentionModel.fromAssessment==='function'){
            const protocol=retentionModel.fromAssessment(this.contentStore.content,completed,this.contentStore.activeCourseId);
            if(protocol){this.appState.setCourseRetention(protocol,this.contentStore.activeCourseId);completed.retentionProtocol=retentionModel.status(protocol,completed.completedAt);}
          }
          this.appState.state.lastBilan=completed;
          this.appState.save();
          this.journal.record('complete_session',completed);
          return 'bilan';
        }
        this.session.currentIndex+=1;
        if(policy.recordProgress!==false)this.appState.mergeSessionIntoProgress();
        this.appState.save();
        this.journal.record('next_activity',this.snapshot());
        return 'session';
      }
      summary(){
        const answers=this.session.answers||{};const queue=this.queue();const activities=queue.map(id=>this.contentStore.content.activities.find(a=>a.id===id)).filter(Boolean);
        const correct=Object.values(answers).filter(a=>a.correct).length;const review=activities.filter(a=>answers[a.id]&&!answers[a.id].correct).map(a=>a.id);const mode=this.session.mode||'training';const policy=this.modePolicy();const remediation=this.session.remediation||null;const reviewPlan=this.session.reviewPlan||null;const guided=policy.id==='review';
        const normalizeObjective=value=>String(value||'Objectif').trim();const objectiveKey=value=>normalizeObjective(value).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'objectif';
        const assessmentEvidence=policy.assessment?activities.filter(activity=>answers[activity.id]).map(activity=>({id:activity.id,objective:normalizeObjective(activity.objective||activity.question),objectiveKey:objectiveKey(activity.objective||activity.question),correct:!!answers[activity.id].correct,role:String(activity.assessment_role||''),type:String(activity.type||''),at:String(answers[activity.id].at||'')})):[];
        const objectiveMap=new Map();for(const row of assessmentEvidence){const current=objectiveMap.get(row.objectiveKey)||{key:row.objectiveKey,label:row.objective,total:0,correct:0,incorrect:0,activityIds:[]};current.total+=1;current.correct+=row.correct?1:0;current.incorrect+=row.correct?0:1;current.activityIds.push(row.id);objectiveMap.set(row.objectiveKey,current);}
        const objectiveAssessment=[...objectiveMap.values()].map(row=>({...row,status:row.incorrect>0?'fragile':(row.correct>=row.total&&row.total>0?'strong':'unverified')}));
        const base={done:Object.keys(answers).length,correct,total:this.total,review,mode,modePolicy:policy,modePlan:this.session.modePlan||null,remediation,reviewPlan,remediationClosed:guided&&review.length===0,remediationPartial:guided&&review.length>0,nextBestStep:review.length?(guided?'Faire une pause ou reprendre les points restants':'Reprendre les points à revoir'):(policy.id==='review'?'Révision terminée':'Nouvelle série'),assessmentEvidence,objectiveAssessment,completedAt:nowIso(),contentVersion:this.contentStore.content.contentVersion};
        const model=window.LearnItSessionModeModel;const modeOutcome=model&&typeof model.outcome==='function'?model.outcome(base):null;const nextModel=window.LearnItNextActionModel;const progress=this.appState.courseProgress(this.contentStore.activeCourseId);const nextAction=nextModel&&typeof nextModel.recommend==='function'?nextModel.recommend(this.contentStore.content,progress,{status:'idle'}, {...base,modeOutcome}):null;return {...base,modeOutcome,nextAction};
      }
      mastery(){const all=this.contentStore.content.activities;const answers=this.session.answers||{};const rows=all.map(a=>({id:a.id,objective:a.objective,seen:!!answers[a.id],mastered:!!answers[a.id]?.correct,review:!!answers[a.id]&&!answers[a.id].correct}));return {mastered:rows.filter(r=>r.mastered).length,review:rows.filter(r=>r.review).length,total:all.length,rows};}
      snapshot(){const policy=this.modePolicy();return {status:this.session.status,mode:this.session.mode||policy.id,policyId:policy.id,feedbackTiming:policy.feedbackTiming,recordProgress:policy.recordProgress,currentIndex:this.session.currentIndex,position:this.session.currentIndex+1,total:this.total,answers:Object.keys(this.session.answers||{}).length,contentVersion:this.session.contentVersion,queue:this.queue()};}
    }

    class LearningMirror{
      constructor(session){this.session=session;}
      status(){const s=this.session.session;if(s.status==='active')return {kind:'active',label:`Séance en cours ${s.currentIndex+1}/${this.session.total}`,position:s.currentIndex+1,total:this.session.total};if(s.status==='completed')return {kind:'done',label:'Séance terminée',position:this.session.total,total:this.session.total};return {kind:'idle',label:'Prêt à commencer',position:0,total:this.session.total};}
      assert(){const st=this.status();const s=this.session.session;if(s.status==='active'&&st.position!==s.currentIndex+1)return {ok:false,reason:'state_mirror_mismatch'};return {ok:true};}
    }

    function learnitStableHash(text){
      let h=2166136261;
      for(let i=0;i<String(text).length;i++){h^=String(text).charCodeAt(i);h=Math.imul(h,16777619);}
      return h>>>0;
    }
    function learnitShuffleSeed(runtime){
      const s=runtime&&runtime.session&&runtime.session.session;
      if(s){
        if(!s.shuffleSeed){
          s.shuffleSeed=nowIso()+'-'+Math.random().toString(36).slice(2);
          try{runtime.appState&&runtime.appState.save&&runtime.appState.save();}catch(e){}
        }
        return s.shuffleSeed;
      }
      return 'preview-stable';
    }
    function learnitStableShuffle(items,key){
      const out=Array.isArray(items)?[...items]:[];
      let seed=learnitStableHash(key)||1;
      for(let i=out.length-1;i>0;i--){
        seed=(Math.imul(seed,1664525)+1013904223)>>>0;
        const j=seed%(i+1);
        const tmp=out[i];out[i]=out[j];out[j]=tmp;
      }
      if(out.length>1&&out.every((v,i)=>v===items[i])){const first=out.shift();out.push(first);}
      return out;
    }
    function activityRetryNonce(runtime,activity){
      const s=runtime&&runtime.session&&runtime.session.session||{};
      const map=s.retryNonceByActivity||{};
      return Number(map[(activity&&activity.id)||'']||0);
    }
    function activityShuffleKey(runtime,activity,scope,length){
      return learnitShuffleSeed(runtime)+'|'+(activity&&activity.id||activity&&activity.question||'activity')+'|'+scope+'|'+String(length||0)+'|retry:'+activityRetryNonce(runtime,activity);
    }
    function makeOrderInitial(activity,runtime){
      if(window.LearnItOrderActivity&&typeof window.LearnItOrderActivity.makeInitial==='function')return window.LearnItOrderActivity.makeInitial(activity,runtime,learnitStableShuffle,activityShuffleKey);
      const values=Array.isArray(activity.tokens)?[...activity.tokens]:[];
      if(values.length<=1)return values;
      return learnitStableShuffle(values, activityShuffleKey(runtime,activity,'order.tokens',values.length));
    }

    class AnswerController{
      constructor(runtime){this.runtime=runtime;this.reset();}
      policy(){return this.runtime.session.modePolicy();}
      deferredFeedback(result){const policy=this.policy();return policy.feedbackTiming==='deferred'?{deferred:true,submitted:true,mode:policy.id,label:policy.label}:result;}
      makeInitialPending(activity){
        const a=activity||null;
        if(!a)return null;
        if(a.type==='fill')return (window.LearnItFillActivity&&typeof window.LearnItFillActivity.makeInitial==='function')?window.LearnItFillActivity.makeInitial(a):Array((a.answer||[]).length).fill('');
        if(a.type==='matching')return (window.LearnItMatchingActivity&&typeof window.LearnItMatchingActivity.makeInitial==='function')?window.LearnItMatchingActivity.makeInitial(a,this.runtime):{matches:{},selectedRight:null};
        if(a.type==='order')return makeOrderInitial(a,this.runtime);
        if(a.type==='flashcard')return (window.LearnItFlashcardActivity&&typeof window.LearnItFlashcardActivity.makeInitial==='function')?window.LearnItFlashcardActivity.makeInitial(a):{revealed:false,grade:null};
        if(a.type==='qcm')return (window.LearnItQcmActivity&&typeof window.LearnItQcmActivity.makeInitial==='function')?window.LearnItQcmActivity.makeInitial(a):null;
        return null;
      }
      clearTransientState(){this.selectedOrderToken=null;this.selectedFillIndex=null;this.feedback=null;}
      reset(){this.clearTransientState();this.pending=this.makeInitialPending(this.runtime.session.currentActivity());}
      selectQcm(i){if(this.feedback)return;const a=this.runtime.session.currentActivity();const api=window.LearnItQcmActivity;if(api&&typeof api.selectChoice==='function'){const result=api.selectChoice(a,this.pending,i);this.pending=result.pending;if(result.changed)this.runtime.journal.record('validated_qcm_choice_select',{index:result.selectedIndex,previousIndex:result.previousIndex,module:'LearnItQcmActivity'});else this.runtime.journal.record('qcm_choice_ignored',{index:i,reason:result.reason||'unchanged',module:'LearnItQcmActivity'});this.runtime.render();return;}this.pending=i;this.runtime.render();}
      fillToken(token){if(this.feedback)return;const a=this.runtime.session.currentActivity();const api=window.LearnItFillActivity;if(api&&typeof api.placeToken==='function'){const result=api.placeToken(a,this.pending,token,this.selectedFillIndex);this.pending=result.values;this.selectedFillIndex=Number.isInteger(result.nextSelectedIndex)&&result.nextSelectedIndex>=0?result.nextSelectedIndex:null;if(result.changed){this.runtime.journal.record('validated_fill_token_place',{token,index:result.placedIndex,module:'LearnItFillActivity'});}else{this.runtime.journal.record('fill_token_ignored',{token,reason:result.reason||'unchanged',module:'LearnItFillActivity'});}this.runtime.render();return;}const values=Array.isArray(this.pending)?[...this.pending]:Array(a.answer.length).fill('');const next=values.findIndex(v=>!v);if(next>=0)values[next]=token;this.pending=values;this.runtime.render();}
      selectFillSlot(index){if(this.feedback)return;const a=this.runtime.session.currentActivity();const values=Array.isArray(this.pending)?this.pending:[];const i=Number(index);if(values[i]){this.clearFill(i);return;}this.selectedFillIndex=i;this.runtime.journal.record('fill_slot_selected',{index:i,module:'LearnItFillActivity'});this.runtime.render();}
      clearFill(index){if(this.feedback)return;const a=this.runtime.session.currentActivity();const api=window.LearnItFillActivity;if(api&&typeof api.clearIndex==='function'){const result=api.clearIndex(a,this.pending,index);this.pending=result.values;this.selectedFillIndex=Number.isInteger(result.nextSelectedIndex)?result.nextSelectedIndex:Number(index);if(result.changed)this.runtime.journal.record('validated_fill_slot_clear',{index:Number(index),token:result.cleared,module:'LearnItFillActivity'});this.runtime.render();return;}const values=Array.isArray(this.pending)?[...this.pending]:[];values[index]='';this.pending=values;this.selectedFillIndex=Number(index);this.runtime.render();}
      selectMatchLeft(left){if(this.feedback)return;const api=window.LearnItMatchingActivity;if(api&&typeof api.selectLeft==='function'){const result=api.selectLeft(this.pending,left);this.pending=result.pending;if(result.changed){this.runtime.journal.record('validated_matching_drop',{left:result.drop.left,right:result.drop.right,module:'LearnItMatchingActivity'});}this.runtime.render();return;}const p=this.pending&&this.pending.matches?deepClone(this.pending):{matches:{},selectedRight:null};if(p.selectedRight)this.dragMatch(left,p.selectedRight);else this.runtime.render();}
      chooseMatch(right){if(this.feedback)return;const api=window.LearnItMatchingActivity;if(api&&typeof api.chooseRight==='function'){this.pending=api.chooseRight(this.pending,right);this.runtime.render();return;}const p=this.pending&&this.pending.matches?deepClone(this.pending):{matches:{},selectedRight:null};p.selectedRight=p.selectedRight===right?null:right;this.pending=p;this.runtime.render();}
      clearMatch(left){if(this.feedback)return;const api=window.LearnItMatchingActivity;if(api&&typeof api.clearLeft==='function'){const result=api.clearLeft(this.pending,left);this.pending=result.pending;this.runtime.render();return;}const p=this.pending&&this.pending.matches?deepClone(this.pending):{matches:{},selectedRight:null};delete p.matches[left];this.pending=p;this.runtime.render();}
      dragMatch(left,right){if(this.feedback||!left||!right)return;const api=window.LearnItMatchingActivity;if(api&&typeof api.assignMatch==='function'){const result=api.assignMatch(this.pending,left,right);this.pending=result.pending;this.runtime.journal.record('validated_matching_drop',{left,right,module:'LearnItMatchingActivity'});this.runtime.render();return;}const p=this.pending&&this.pending.matches?deepClone(this.pending):{matches:{},selectedRight:null};for(const k of Object.keys(p.matches)){if(p.matches[k]===right&&k!==left)delete p.matches[k];}p.matches[left]=right;p.selectedRight=null;this.pending=p;this.runtime.journal.record('validated_matching_drop',{left,right});this.runtime.render();}
      orderTokensEqual(a,b){
        if(window.LearnItOrderActivity&&typeof window.LearnItOrderActivity.tokensEqual==='function')return window.LearnItOrderActivity.tokensEqual(a,b);
        const ca=new Map(), cb=new Map();
        (Array.isArray(a)?a:[]).forEach(v=>ca.set(v,(ca.get(v)||0)+1));
        (Array.isArray(b)?b:[]).forEach(v=>cb.set(v,(cb.get(v)||0)+1));
        if(ca.size!==cb.size)return false;
        for(const [k,v] of ca){if(cb.get(k)!==v)return false;}
        return true;
      }
      ensureOrderPending(reason='operation'){
        const a=this.runtime.session.currentActivity();
        if(!a||a.type!=='order')return Array.isArray(this.pending)?this.pending:[];
        const tokens=Array.isArray(a.tokens)?a.tokens:[];
        let values=Array.isArray(this.pending)?[...this.pending]:[];
        const valid=this.orderTokensEqual(values,tokens);
        if(valid){this.pending=values;return this.pending;}
        const fallback=makeOrderInitial(a,this.runtime);
        this.pending=(window.LearnItOrderActivity&&typeof window.LearnItOrderActivity.repairPending==='function')?window.LearnItOrderActivity.repairPending(values,tokens,fallback):fallback;
        if(this.selectedOrderToken&&!this.pending.includes(this.selectedOrderToken))this.selectedOrderToken=null;
        this.runtime.journal.record('order_state_repaired',{reason,activityId:a.id||'',expected:tokens.length,actual:values.length,repaired:this.pending.length,module:'LearnItOrderActivity'});
        return this.pending;
      }
      orderToken(token){if(this.feedback)return;this.ensureOrderPending('select');this.selectedOrderToken=token;this.runtime.render();}
      clearOrder(token){if(this.feedback)return;this.ensureOrderPending('clear');this.pending=(Array.isArray(this.pending)?this.pending:[]).filter(t=>t!==token);if(this.selectedOrderToken===token)this.selectedOrderToken=null;this.runtime.render();}
      moveOrder(token,dir){if(this.feedback)return;if(this.runtime.drag)this.runtime.cleanupDrag(true);const values=[...this.ensureOrderPending('move')];const moved=(window.LearnItOrderActivity&&typeof window.LearnItOrderActivity.moveTokenByDelta==='function')?window.LearnItOrderActivity.moveTokenByDelta(values,token,dir):null;if(moved?moved.changed:false){this.pending=moved.values;this.selectedOrderToken=token;this.runtime.journal.record('validated_order_button_move',{token,dir:Number(dir||0),from:moved.from,to:moved.to,module:'LearnItOrderActivity'});this.runtime.render();return;}const i=values.indexOf(token);const j=i+Number(dir||0);if(i>=0&&j>=0&&j<values.length){const tmp=values[i];values[i]=values[j];values[j]=tmp;this.pending=values;this.selectedOrderToken=token;this.runtime.journal.record('validated_order_button_move',{token,dir:Number(dir||0),from:i,to:j});this.runtime.render();}}
      moveSelectedOrder(dir){if(this.feedback||!this.selectedOrderToken)return;this.moveOrder(this.selectedOrderToken,dir);}
      moveOrderToIndex(token,index){if(this.feedback||!token)return;const values=[...this.ensureOrderPending('drop')];const moved=(window.LearnItOrderActivity&&typeof window.LearnItOrderActivity.moveTokenToIndex==='function')?window.LearnItOrderActivity.moveTokenToIndex(values,token,index):null;if(moved&&moved.from<0){this.runtime.journal.record('order_drop_ignored_missing_token',{token,index,module:'LearnItOrderActivity'});return;}if(moved){this.pending=moved.values;this.selectedOrderToken=token;this.runtime.journal.record('validated_order_live_insert',{token,index:moved.to,from:moved.from,module:'LearnItOrderActivity'});this.runtime.render();return;}const from=values.indexOf(token);if(from<0){this.runtime.journal.record('order_drop_ignored_missing_token',{token,index});return;}values.splice(from,1);const to=Math.max(0,Math.min(Number(index)||0,values.length));values.splice(to,0,token);this.pending=values;this.selectedOrderToken=token;this.runtime.journal.record('validated_order_live_insert',{token,index:to,from});this.runtime.render();}
      moveOrderTo(token,targetToken,placement){if(this.feedback||!token||!targetToken||token===targetToken)return;const values=[...this.ensureOrderPending('move-to')];const from=values.indexOf(token);if(from<0)return;values.splice(from,1);let to=values.indexOf(targetToken);if(to<0){values.splice(from,0,token);this.pending=values;return;}if(placement==='after')to+=1;this.moveOrderToIndex(token,to);}
      revealFlashcard(){if(this.feedback)return;const api=window.LearnItFlashcardActivity;if(api&&typeof api.reveal==='function'){const result=api.reveal(this.pending);this.pending=result.pending;if(result.changed)this.runtime.journal.record('validated_flashcard_reveal',{module:'LearnItFlashcardActivity'});this.runtime.render();return;}const p=this.pending&&typeof this.pending==='object'?deepClone(this.pending):{};p.revealed=true;this.pending=p;this.runtime.render();}
      gradeFlashcard(correct){if(this.feedback)return;const a=this.runtime.session.currentActivity();const api=window.LearnItFlashcardActivity;let actual;if(api&&typeof api.grade==='function'){const result=api.grade(a,this.pending,correct);this.pending=result.pending;actual=result.feedback;this.runtime.journal.record('validated_flashcard_grade',{correct:!!correct,module:'LearnItFlashcardActivity'});}else{const answerText=String(a.answer||a.back||'');const ok=!!correct;this.pending={revealed:true,grade:ok};actual={correct:ok,expected:answerText,why:a.why||answerText,remediation:a.remediation||'Marque cette carte à revoir puis relis la définition.'};}this.runtime.session.saveAnswer(actual);this.feedback=this.deferredFeedback(actual);this.runtime.render();}
      validate(){const a=this.runtime.session.currentActivity();let correct=false, expected='';if(a.type==='qcm'){const api=window.LearnItQcmActivity;correct=(api&&typeof api.isCorrect==='function')?api.isCorrect(a,this.pending):this.pending===a.answer;expected=(api&&typeof api.expectedText==='function')?api.expectedText(a):a.choices[a.answer];}if(a.type==='fill'){const api=window.LearnItFillActivity;const values=(api&&typeof api.normalizePending==='function')?api.normalizePending(a,this.pending):(Array.isArray(this.pending)?this.pending:[]);correct=(api&&typeof api.isCorrect==='function')?api.isCorrect(a,this.pending):JSON.stringify(values)===JSON.stringify(a.answer);expected=(api&&typeof api.expectedText==='function')?api.expectedText(a):(a.sentence||a.answer.join(' '));}if(a.type==='matching'){const api=window.LearnItMatchingActivity;const matches=(this.pending&&this.pending.matches)||{};correct=(api&&typeof api.isCorrect==='function')?api.isCorrect(a,this.pending):a.pairs.every(([l,r])=>matches[l]===r);expected=(api&&typeof api.expectedText==='function')?api.expectedText(a):a.pairs.map(p=>p.join(' → ')).join(' ; ');}if(a.type==='order'){const values=Array.isArray(this.pending)?this.pending:[];correct=JSON.stringify(values)===JSON.stringify(a.answer);expected=a.answer.join(' → ');}if(a.type==='flashcard'){return this.gradeFlashcard(!!(this.pending&&this.pending.grade));}const remediationMeta=(window.LearnItRemediationModel&&typeof window.LearnItRemediationModel.feedback==='function')?window.LearnItRemediationModel.feedback(a,correct):{commonErrors:correct?[]:(a.common_errors||[]),remediation:a.remediation||''};const actual={correct,expected,why:a.why,remediation:a.remediation||remediationMeta.remediation||'Reprends la règle puis retente.',commonErrors:remediationMeta.commonErrors||[],objective:a.objective||''};this.runtime.session.saveAnswer(actual);this.feedback=this.deferredFeedback(actual);this.runtime.render();}
      retry(){if(!this.policy().allowRetry)return;const a=this.runtime.session.currentActivity();const s=this.runtime.session.session;if(s&&a){if(!s.retryNonceByActivity)s.retryNonceByActivity={};s.retryNonceByActivity[a.id]=Number(s.retryNonceByActivity[a.id]||0)+1;this.runtime.appState.save();}this.reset();if(this.runtime.renderer&&this.runtime.renderer.qcmOrders)this.runtime.renderer.qcmOrders={};this.runtime.render();}
      continue(){this.feedback=null;const next=this.runtime.session.moveNext();this.reset();this.runtime.go(next);this.runtime.scrollTop();}
    }

    class ActivityRenderer{
      constructor(runtime){this.runtime=runtime;this.qcmOrders={};this.shuffleOrders={};}
      qcmShuffleSeed(){
        const s=this.runtime.session.session||{};
        if(!s.shuffleSeed){
          s.shuffleSeed=nowIso()+'-'+Math.random().toString(36).slice(2);
          this.runtime.appState.save();
        }
        return s.shuffleSeed;
      }
      qcmHash(text){return learnitStableHash(text);}
      qcmOrder(a){
        const length=Array.isArray(a.choices)?a.choices.length:0;
        const nonce=activityRetryNonce(this.runtime,a);
        const key=this.qcmShuffleSeed()+'|'+(a.id||a.question||'qcm')+'|'+length+'|retry:'+nonce;
        if(this.qcmOrders[key])return this.qcmOrders[key];
        const order=Array.from({length},(_,i)=>i);
        let seed=this.qcmHash(key)||1;
        for(let i=order.length-1;i>0;i--){
          seed=(Math.imul(seed,1664525)+1013904223)>>>0;
          const j=seed%(i+1);
          const tmp=order[i];order[i]=order[j];order[j]=tmp;
        }
        if(order.length>1&&order.every((v,i)=>v===i)){
          const first=order.shift();order.push(first);
        }
        this.qcmOrders[key]=order;
        return order;
      }
      shuffledItems(a,scope,items){
        const key=activityShuffleKey(this.runtime,a,scope,Array.isArray(items)?items.length:0);
        if(!this.shuffleOrders[key])this.shuffleOrders[key]=learnitStableShuffle(items,key);
        return this.shuffleOrders[key];
      }
      render(activity,answer){if(!activity)return '<div class="feedback warn"><strong>Activité introuvable</strong></div>';if(activity.type==='qcm')return this.qcm(activity,answer);if(activity.type==='fill')return this.fill(activity,answer);if(activity.type==='matching')return this.matching(activity,answer);if(activity.type==='order')return this.order(activity,answer);if(activity.type==='flashcard')return this.flashcard(activity,answer);return '<div class="feedback warn"><strong>Type non pris en charge</strong></div>';}
      assetById(id){
        if(!id)return null;
        const pools=[];
        const active=this.runtime.contentStore&&this.runtime.contentStore.content;
        if(active&&Array.isArray(active.assets))pools.push(active.assets);
        const courses=this.runtime.contentStore&&typeof this.runtime.contentStore.allCourses==='function'?this.runtime.contentStore.allCourses():[];
        for(const course of courses){if(course&&Array.isArray(course.assets))pools.push(course.assets);}
        for(const assets of pools){const hit=assets.find(asset=>asset&&asset.id===id);if(hit)return hit;}
        return null;
      }
      hardenSvg(svg,alt='Visuel pédagogique'){
        const model=window.LearnItMediaSecurityModel;
        if(!model||typeof model.sanitizeSvg!=='function')return '';
        const result=model.sanitizeSvg(svg,{alt});
        return result&&result.ok?result.svg:'';
      }
      mediaFallback(message,detail=''){return `<div class="media-fallback"><strong>${escapeHtml(message)}</strong>${detail?`<div class="tiny">${escapeHtml(detail)}</div>`:''}</div>`;}
      mediaHtml(a,placement='question'){
        const refs=(Array.isArray(a.media)?a.media:[]).filter(m=>(m.placement||'question')===placement);
        if(!refs.length)return '';
        const cards=refs.map(ref=>{
          const asset=this.assetById(ref.assetId);
          if(!asset)return `<div class="feedback warn"><strong>Visuel introuvable</strong><span class="tiny">${escapeHtml(ref.assetId||'?')}</span></div>`;
          const caption=ref.caption||asset.caption||'';
          const alt=asset.alt||caption||'Visuel pédagogique';
          const data=String(asset.data||asset.src||asset.url||asset.source_url||'').trim();
          const format=String(asset.format||'').toLowerCase();
          let body='';let state='unsupported';
          if((format==='svg'||/^<svg[\s>]/i.test(data))&&data){
            const svg=this.hardenSvg(data,alt);
            body=svg?`<div class="media-svg-wrap">${svg}</div>`:this.mediaFallback('SVG non affichable',asset.id||'');
            state=svg?'rendered-svg':'fallback';
          }else{
            const model=window.LearnItMediaSecurityModel;
            const source=model&&typeof model.safeImageSource==='function'?model.safeImageSource(data):{ok:false,reason:'media-security-model-missing'};
            if(source.ok){
              body=`<img src="${escapeAttr(source.src)}" alt="${escapeAttr(alt)}" loading="lazy" decoding="async" referrerpolicy="no-referrer" crossorigin="anonymous" data-learnit-media="image">`;
              state='rendered-image';
            }else{
              body=this.mediaFallback('Format média non affichable',source.reason||format||'données manquantes');
              state='fallback';
            }
          /* rc684 source policy branch */
          }
          return `<button type="button" class="media-figure" data-action="toggle-media-zoom" data-media-asset-id="${escapeAttr(asset.id||ref.assetId||'')}" aria-label="Agrandir le visuel"><div class="media-frame" data-media-state="${escapeAttr(state)}">${body}</div>${caption?`<div class="media-caption">${escapeHtml(caption)}<span class="media-zoom-hint">Toucher pour agrandir / réduire.</span></div>`:''}</button>`;
        }).join('');
        return `<div class="media-stack" data-media-count="${refs.length}">${cards}</div>`;
      }
      qcm(a,ans){
        const api=window.LearnItQcmActivity;
        const selected=(api&&typeof api.normalizePending==='function')?api.normalizePending(a,ans.pending):ans.pending;
        const locked=!!ans.feedback;
        const media=this.mediaHtml(a);
        const order=this.qcmOrder(a);
        const states=(api&&typeof api.choiceStates==='function')?api.choiceStates(a,selected,locked):(a.choices||[]).map((choice,index)=>({choice,index,selected:selected===index,correct:locked&&index===a.answer,wrong:locked&&selected===index&&index!==a.answer}));
        const byIndex=new Map(states.map(state=>[state.index,state]));
        const choices=order.map((index,displayIndex)=>{
          const state=byIndex.get(index)||{choice:(a.choices||[])[index],index};
          let cls='choice';
          if(state.selected)cls+=' selected';
          if(state.correct)cls+=' correct';
          if(state.wrong)cls+=' wrong';
          const visualState=state.correct?'correct':state.wrong?'wrong':state.selected?'selected':'idle';
          return `<button type="button" role="radio" class="${cls}" data-action="select-qcm" data-qcm-choice="${index}" data-index="${index}" data-display-order="${displayIndex}" data-qcm-state="${visualState}" aria-checked="${state.selected?'true':'false'}" aria-pressed="${state.selected?'true':'false'}" ${locked?'disabled':''}>${escapeHtml(state.choice)}</button>`;
        }).join('');
        const phase=locked?'feedback':selected===null?'idle':'selected';
        return `<div class="stack activity-qcm randomized-answers ${media?'has-media':''}" data-activity-type="qcm" data-qcm-module="LearnItQcmActivity" data-qcm-phase="${phase}" data-randomized="true">${media}<div class="activity-answer-panel" role="radiogroup" aria-label="Choix de réponse">${choices}</div></div>`;
      }
      fill(a,ans){const api=window.LearnItFillActivity;const values=(api&&typeof api.normalizePending==='function')?api.normalizePending(a,ans.pending):(Array.isArray(ans.pending)?ans.pending:Array(a.answer.length).fill(''));const selected=Number.isInteger(this.runtime.answer.selectedFillIndex)?this.runtime.answer.selectedFillIndex:null;let sentence='';a.parts.forEach(part=>{if(typeof part==='number'){const v=values[part]||'';const isSelected=selected===part&&!v;sentence+=`<button type="button" class="slot ${v?'':'empty'} ${isSelected?'selected':''}" data-action="select-fill-slot" data-fill-slot="${part}" data-index="${part}" aria-label="Réponse ${part+1}${v?': '+escapeAttr(v):''}" aria-selected="${isSelected?'true':'false'}">${v?escapeHtml(v):'…'}</button>`;}else sentence+=escapeHtml(part);});const sourceTokens=(api&&typeof api.effectiveTokens==='function')?api.effectiveTokens(a):(Array.isArray(a.tokens)?a.tokens:[]);const ordered=this.shuffledItems(a,'fill.tokens',sourceTokens);const states=(api&&typeof api.tokenStates==='function')?api.tokenStates(Object.assign({},a,{tokens:ordered}),values):ordered.map(t=>({token:t,used:values.includes(t),remainingCount:values.includes(t)?0:1,reusable:false}));return `<div data-activity-type="fill" data-randomized="true">${this.mediaHtml(a)}<div class="fill-sentence">${sentence}</div><div class="bank" aria-label="Mots disponibles">${states.map(s=>{const remaining=s.reusable&&s.remainingCount>0?`<span class="token-remaining" aria-hidden="true">×${s.remainingCount}</span>`:'';const availability=s.reusable?`, utilisable encore ${s.remainingCount} fois`:'';return `<button type="button" class="token ${s.used?'used':''}" data-action="fill-token" data-fill-token="${escapeAttr(s.token)}" data-token="${escapeAttr(s.token)}" aria-label="${escapeAttr(s.token+availability)}" aria-disabled="${s.used?'true':'false'}" ${s.used?'disabled':''}><span>${escapeHtml(s.token)}</span>${remaining}</button>`;}).join('')}</div><p class="tiny">Touche un emplacement puis un mot. Sans emplacement choisi, le prochain vide est rempli. Aucun clavier mobile n’est ouvert.</p></div>`;}

      matching(a,ans){
        const p=ans.pending&&ans.pending.matches?ans.pending:{matches:{},selectedRight:null};
        const rows=this.shuffledItems(a,'matching.rows',Array.isArray(a.pairs)?a.pairs:[]);
        const rights=this.shuffledItems(a,'matching.rights',(Array.isArray(a.pairs)?a.pairs:[]).map(pair=>pair[1]));
        const usedRights=new Set(Object.values(p.matches));
        const unplaced=rights.filter(r=>!usedRights.has(r));
        const done=Object.keys(p.matches).length;
        return `<div data-activity-type="matching" data-randomized="true" class="match-board">${this.mediaHtml(a)}<div class="match-layout"><div class="label-bank-wrap ${unplaced.length?'':'hidden'}" aria-label="Réponses à placer"><div class="section-title">À placer</div><div class="label-bank">${unplaced.map(r=>`<button type="button" class="label-card ${p.selectedRight===r?'selected':''}" data-action="choose-match" data-drag-match-right="${escapeAttr(r)}" data-right="${escapeAttr(r)}" aria-label="Placer ${escapeAttr(r)}">${escapeHtml(r)}</button>`).join('')}</div></div><div class="matching-board" aria-label="Notations fixes et réponses déposées">${rows.map(([l])=>{const placed=p.matches[l];const expected=a.pairs.find(([left])=>left===l)?.[1];const evalCls=ans.feedback?(placed===expected?' correct-line':' wrong-line'):'';const zone=placed?`<div class="drop-zone filled${evalCls}" data-match-left="${escapeAttr(l)}" data-left="${escapeAttr(l)}" aria-label="Réponse déposée pour ${escapeAttr(l)}"><button type="button" class="label-card placed ${p.selectedRight===placed?'selected':''}" data-action="clear-match" data-left="${escapeAttr(l)}" aria-label="Retirer ${escapeAttr(placed)} de ${escapeAttr(l)} et le remettre à placer">${escapeHtml(placed)}</button></div>`:`<button type="button" class="drop-zone ${p.selectedRight?' hot':''}${evalCls}" data-action="select-match-left" data-match-left="${escapeAttr(l)}" data-left="${escapeAttr(l)}" aria-label="Case réponse pour ${escapeAttr(l)}"></button>`;return `<div class="match-row${evalCls}" data-match-row="${escapeAttr(l)}"><div class="fixed-term">${escapeHtml(l)}</div>${zone}</div>`;}).join('')}</div></div></div>`;
      }
      order(a,ans){
        const values=typeof ans.ensureOrderPending==='function'?ans.ensureOrderPending('render'):(Array.isArray(ans.pending)&&ans.pending.length?ans.pending:makeOrderInitial(a,this.runtime));
        const drag=this.runtime.drag&&this.runtime.drag.type==='order'?this.runtime.drag:null;
        const selected=ans.selectedOrderToken;
        const model=(window.LearnItOrderActivity&&typeof window.LearnItOrderActivity.buildRenderModel==='function')?window.LearnItOrderActivity.buildRenderModel(values,selected,drag):null;
        const preview=model?model.preview:values.filter(t=>!drag||t!==drag.token);
        const placeholderHeight=model?model.placeholderHeight:(drag?Math.max(48,Math.round(Number(drag.placeholderHeight)||drag.sourceRect?.height||66)):66);
        const selectedIndex=model?model.selectedIndex:(selected?values.indexOf(selected):-1);
        return `<div data-activity-type="order" data-randomized="true" class="order-area" data-order-module="LearnItOrderActivity">${this.mediaHtml(a)}<div class="order-board" aria-label="Cartes à réordonner">${preview.map(t=>t==='__placeholder__'?`<div class="order-placeholder" data-order-drag-placeholder="true" aria-hidden="true" style="--order-placeholder-height:${placeholderHeight}px"></div>`:`<button class="order-card ${selected===t?'selected':''} ${drag&&drag.token===t?'drag-source':''}" data-action="order-token" data-token="${escapeAttr(t)}" data-drag-order-token="${escapeAttr(t)}" aria-selected="${selected===t?'true':'false'}" aria-label="Étape : ${escapeAttr(t)}"><span class="order-text">${escapeHtml(t)}</span></button>`).join('')}</div><div class="order-toolbar" aria-label="Commandes de déplacement"><button data-action="order-move-selected" data-dir="-1" ${selectedIndex<=0?'disabled':''} aria-label="Monter l’étape sélectionnée">↑</button><button data-action="order-move-selected" data-dir="1" ${selectedIndex<0||selectedIndex===values.length-1?'disabled':''} aria-label="Descendre l’étape sélectionnée">↓</button></div></div>`;
      }
      flashcard(a,ans){const api=window.LearnItFlashcardActivity;const p=(api&&typeof api.normalizePending==='function')?api.normalizePending(ans.pending):(ans.pending&&typeof ans.pending==='object'?ans.pending:{revealed:false});const front=a.front||a.question;const back=(api&&typeof api.expectedText==='function')?api.expectedText(a):(a.back||a.answer||'');return `<div data-activity-type="flashcard" data-flashcard-module="LearnItFlashcardActivity" data-flashcard-revealed="${p.revealed?'true':'false'}" class="flashcard-area">${this.mediaHtml(a)}<div class="flashcard-box"><div class="flashcard-kicker">Rappel actif</div><div class="flashcard-face front">${escapeHtml(front)}</div>${p.revealed?`<div class="flashcard-face back">${escapeHtml(back)}</div><div class="flashcard-actions"><button type="button" class="primary" data-action="flashcard-grade" data-correct="true">Je savais</button><button type="button" data-action="flashcard-grade" data-correct="false">À revoir</button></div>`:`<div class="flashcard-actions"><button type="button" class="primary" data-action="flashcard-reveal">Afficher la réponse</button></div>`}</div></div>`;}
    }

