(function(){
  'use strict';

  function asPairs(activity){
    return Array.isArray(activity && activity.pairs) ? activity.pairs.filter(pair => Array.isArray(pair) && pair.length >= 2) : [];
  }

  function makeInitial(){
    return {matches:{}, selectedRight:null};
  }

  function normalizePending(pending){
    const p = pending && typeof pending === 'object' ? pending : {};
    const matches = p.matches && typeof p.matches === 'object' ? Object.assign({}, p.matches) : {};
    return {matches, selectedRight:p.selectedRight || null};
  }

  function chooseRight(pending, right){
    const p = normalizePending(pending);
    p.selectedRight = p.selectedRight === right ? null : right;
    return p;
  }

  function selectLeft(pending, left){
    const p = normalizePending(pending);
    if(!left || !p.selectedRight) return {changed:false, pending:p, drop:null};
    const result = assignMatch(p, left, p.selectedRight);
    return {changed:result.changed, pending:result.pending, drop:{left, right:p.selectedRight}};
  }

  function clearLeft(pending, left){
    const p = normalizePending(pending);
    if(!left || !Object.prototype.hasOwnProperty.call(p.matches, left)) return {changed:false, pending:p};
    delete p.matches[left];
    return {changed:true, pending:p};
  }

  function assignMatch(pending, left, right){
    const p = normalizePending(pending);
    if(!left || !right) return {changed:false, pending:p};
    let changed = p.matches[left] !== right || p.selectedRight !== null;
    for(const key of Object.keys(p.matches)){
      if(p.matches[key] === right && key !== left){
        delete p.matches[key];
        changed = true;
      }
    }
    p.matches[left] = right;
    p.selectedRight = null;
    return {changed, pending:p};
  }

  function isComplete(activity, pending){
    const p = normalizePending(pending);
    return Object.keys(p.matches).length === asPairs(activity).length;
  }

  function isCorrect(activity, pending){
    const p = normalizePending(pending);
    return asPairs(activity).every(([left, right]) => p.matches[left] === right);
  }

  function expectedText(activity){
    return asPairs(activity).map(pair => pair.join(' → ')).join(' ; ');
  }

  function domSnapshot(root){
    const scope = root || document;
    const ghosts = Array.from(document.querySelectorAll('.drag-ghost.label-card'));
    const hot = Array.from(scope.querySelectorAll('.hot'));
    const sources = Array.from(scope.querySelectorAll('[data-drag-match-right].drag-source'));
    return {
      ghosts: ghosts.length,
      hotHints: hot.length,
      sources: sources.length,
      bodyDragActive: !!(document.body && document.body.classList && document.body.classList.contains('drag-active'))
    };
  }

  function auditDomSnapshot(snapshot){
    const s = snapshot || {};
    const issues = [];
    if((s.ghosts || 0) > 1) issues.push('multiple-matching-ghosts');
    if((s.sources || 0) > 1) issues.push('multiple-matching-drag-sources');
    if((s.bodyDragActive || false) && (s.ghosts || 0) === 0) issues.push('drag-active-without-matching-ghost');
    return {ok:issues.length === 0, issues};
  }

  const POINTER_SCHEMA = 'learnit.matching_pointer_controller.rc221.v1';

  function record(runtime, event, payload){
    try{
      if(runtime && runtime.journal && typeof runtime.journal.record === 'function'){
        runtime.journal.record(event, Object.assign({module:'LearnItMatchingActivity.pointer', pointerSchema:POINTER_SCHEMA}, payload || {}));
      }
    }catch(e){/* no-op */}
  }

  function start(runtime, event, data){
    if(!runtime || !event || !data || !data.source || !data.right) return false;
    if(runtime.drag){
      record(runtime, 'drag_orphan_recovered', {previousType:runtime.drag.type, newType:data.type});
      if(typeof runtime.cleanupDrag === 'function') runtime.cleanupDrag(true);
    }
    const rect = data.source.getBoundingClientRect();
    const drag = Object.assign({}, data, {
      type:'matching',
      pointerId:event.pointerId,
      startX:event.clientX,
      startY:event.clientY,
      x:event.clientX,
      y:event.clientY,
      moved:false,
      ghost:null,
      raf:0,
      lastDrop:null,
      sourceRect:{width:rect.width, height:rect.height},
      grabX:event.clientX - rect.left,
      grabY:event.clientY - rect.top,
      offsetX:0,
      offsetY:0,
      watchdog:0,
      controller:POINTER_SCHEMA
    });
    runtime.drag = drag;
    try{data.source.setPointerCapture(event.pointerId);}catch(e){/* no-op */}
    drag.watchdog = setTimeout(()=>{
      if(runtime.drag && runtime.drag.pointerId === event.pointerId && runtime.drag.type === 'matching'){
        record(runtime, 'drag_watchdog_cleanup', {type:drag.type, label:drag.label});
        cleanup(runtime, true);
      }
    }, 9000);
    record(runtime, 'direct_drag_start', {type:'matching', label:data.label, right:data.right});
    return true;
  }

  function activate(runtime, drag){
    if(!drag || drag.type !== 'matching') return false;
    drag.moved = true;
    runtime.suppressNextClick = true;
    createGhost(runtime, drag);
    if(drag.source) drag.source.classList.add('drag-source');
    if(document.body) document.body.classList.add('drag-active');
    return true;
  }

  function move(runtime, event){
    const drag = runtime && runtime.drag;
    if(!drag || drag.type !== 'matching' || !event || event.pointerId !== drag.pointerId) return false;
    drag.x = event.clientX;
    drag.y = event.clientY;
    const dx = drag.x - drag.startX;
    const dy = drag.y - drag.startY;
    if(!drag.moved && Math.hypot(dx, dy) < 4) return true;
    if(!drag.moved) activate(runtime, drag);
    event.preventDefault();
    scheduleFrame(drag);
    updateDrop(runtime, drag);
    return true;
  }

  function createGhost(runtime, drag){
    if(!drag || drag.ghost || typeof document === 'undefined') return null;
    const ghost = document.createElement('div');
    ghost.className = 'drag-ghost label-card';
    ghost.textContent = drag.label || drag.right || '';
    ghost.style.visibility = 'hidden';
    ghost.style.transition = 'none';
    ghost.style.animation = 'none';
    ghost.style.transform = 'translate3d(0,0,0)';
    const viewport = Math.max(180, window.innerWidth - 36);
    const wanted = Math.min(Math.max(drag.sourceRect.width, 120), viewport);
    ghost.style.width = wanted + 'px';
    document.body.appendChild(ghost);
    drag.ghost = ghost;
    const rect = ghost.getBoundingClientRect();
    drag.offsetX = rect.width / 2;
    drag.offsetY = rect.height / 2;
    positionGhost(drag);
    ghost.getBoundingClientRect();
    ghost.style.visibility = 'visible';
    return ghost;
  }

  function positionGhost(drag){
    if(!drag || !drag.ghost) return;
    drag.ghost.style.transform = `translate3d(${drag.x - drag.offsetX}px,${drag.y - drag.offsetY}px,0)`;
  }

  function scheduleFrame(drag){
    if(!drag || drag.raf) return;
    drag.raf = requestAnimationFrame(()=>{
      drag.raf = 0;
      positionGhost(drag);
    });
  }

  function elementUnderDrag(drag){
    if(!drag || typeof document === 'undefined') return null;
    if(drag.ghost) drag.ghost.style.display = 'none';
    const el = document.elementFromPoint(drag.x, drag.y);
    if(drag.ghost) drag.ghost.style.display = '';
    return el;
  }

  function updateDrop(runtime, drag){
    if(runtime && typeof runtime.clearDropHints === 'function') runtime.clearDropHints();
    else if(runtime && runtime.root) runtime.root.querySelectorAll('.hot').forEach(el => el.classList.remove('hot'));
    drag.lastDrop = null;
    const el = elementUnderDrag(drag);
    if(!el || !el.closest) return false;
    const target = el.closest('[data-match-left]');
    if(target){
      target.classList.add('hot');
      const row = target.closest('.match-row');
      if(row) row.classList.add('hot');
      drag.lastDrop = {type:'matching', left:target.dataset.matchLeft, right:drag.right};
      return true;
    }
    return false;
  }

  function end(runtime, event){
    const drag = runtime && runtime.drag;
    if(!drag || drag.type !== 'matching' || !event || event.pointerId !== drag.pointerId) return false;
    if(drag.moved) event.preventDefault();
    const drop = drag.lastDrop;
    const moved = drag.moved;
    cleanup(runtime, true);
    if(moved && drop && drop.type === 'matching') runtime.answer.dragMatch(drop.left, drop.right);
    return true;
  }

  function cancel(runtime, event){
    const drag = runtime && runtime.drag;
    if(!drag || drag.type !== 'matching') return false;
    if(event && event.pointerId !== undefined && event.pointerId !== drag.pointerId) return false;
    cleanup(runtime, true);
    return true;
  }

  function cleanup(runtime, skipRender){
    const drag = runtime && runtime.drag;
    if(!drag || drag.type !== 'matching') return false;
    if(drag.watchdog) clearTimeout(drag.watchdog);
    if(drag.raf) cancelAnimationFrame(drag.raf);
    if(drag.ghost) drag.ghost.remove();
    if(drag.source){
      try{
        if(drag.pointerId !== undefined && drag.source.hasPointerCapture && drag.source.hasPointerCapture(drag.pointerId)) drag.source.releasePointerCapture(drag.pointerId);
      }catch(e){/* no-op */}
      drag.source.classList.remove('drag-source');
    }
    if(document.body) document.body.classList.remove('drag-active');
    if(runtime && typeof runtime.clearDropHints === 'function') runtime.clearDropHints();
    else if(runtime && runtime.root) runtime.root.querySelectorAll('.hot').forEach(el => el.classList.remove('hot'));
    runtime.drag = null;
    if(runtime.suppressNextClick) requestAnimationFrame(()=>{runtime.suppressNextClick = false;});
    if(!skipRender && typeof runtime.render === 'function') runtime.render();
    return true;
  }

  const pointer = Object.freeze({
    schema: POINTER_SCHEMA,
    start, move, end, cancel, cleanup,
    activate, createGhost, positionGhost, scheduleFrame, elementUnderDrag, updateDrop
  });

  window.LearnItMatchingActivity = Object.freeze({
    schema:'learnit.matching_activity.rc221.v1',
    makeInitial,
    normalizePending,
    chooseRight,
    selectLeft,
    clearLeft,
    assignMatch,
    isComplete,
    isCorrect,
    expectedText,
    domSnapshot,
    auditDomSnapshot,
    pointer
  });
})();
