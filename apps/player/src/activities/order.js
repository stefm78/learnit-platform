(function(){
  'use strict';

  function asArray(value){
    return Array.isArray(value) ? value : [];
  }

  function countTokens(values){
    const counts = new Map();
    asArray(values).forEach(value => counts.set(value, (counts.get(value) || 0) + 1));
    return counts;
  }

  function tokensEqual(left, right){
    const a = countTokens(left);
    const b = countTokens(right);
    if (a.size !== b.size) return false;
    for (const [token, count] of a) {
      if (b.get(token) !== count) return false;
    }
    return true;
  }

  function makeInitial(activity, runtime, shuffleFn, keyFn){
    const values = asArray(activity && activity.tokens).slice();
    if (values.length <= 1) return values;
    if (typeof shuffleFn === 'function' && typeof keyFn === 'function') {
      return shuffleFn(values, keyFn(runtime, activity, 'order.tokens', values.length));
    }
    return values;
  }

  function repairPending(pending, tokens, fallback){
    const expected = asArray(tokens).slice();
    const values = asArray(pending).slice();
    if (tokensEqual(values, expected)) return values;
    const repaired = [];
    const needed = countTokens(expected);
    for (const value of values) {
      const remaining = needed.get(value) || 0;
      if (remaining > 0) {
        repaired.push(value);
        needed.set(value, remaining - 1);
      }
    }
    for (const token of expected) {
      const remaining = needed.get(token) || 0;
      for (let i = 0; i < remaining; i += 1) repaired.push(token);
      if (remaining) needed.set(token, 0);
    }
    return repaired.length ? repaired : asArray(fallback).slice();
  }

  function moveTokenByDelta(values, token, delta){
    const next = asArray(values).slice();
    const from = next.indexOf(token);
    const to = from + Number(delta || 0);
    if (from < 0 || to < 0 || to >= next.length) {
      return {changed:false, values:next, from, to};
    }
    const tmp = next[from];
    next[from] = next[to];
    next[to] = tmp;
    return {changed:true, values:next, from, to};
  }

  function moveTokenToIndex(values, token, index){
    const next = asArray(values).slice();
    const from = next.indexOf(token);
    if (from < 0) return {changed:false, values:next, from, to:-1};
    next.splice(from, 1);
    const to = Math.max(0, Math.min(Number(index) || 0, next.length));
    next.splice(to, 0, token);
    return {changed:from !== to, values:next, from, to};
  }

  function buildRenderModel(values, selectedToken, drag){
    const pending = asArray(values).slice();
    const activeDrag = drag && drag.type === 'order' ? drag : null;
    const preview = pending.filter(token => !activeDrag || token !== activeDrag.token);
    const selectedIndex = pending.indexOf(selectedToken);
    const placeholderHeight = activeDrag
      ? Math.max(48, Math.round(Number(activeDrag.placeholderHeight) || (activeDrag.sourceRect && activeDrag.sourceRect.height) || 66))
      : 66;
    if (activeDrag) {
      const idx = Math.max(0, Math.min(Number(activeDrag.overIndex) || 0, preview.length));
      preview.splice(idx, 0, '__placeholder__');
    }
    return {values:pending, preview, selectedIndex, placeholderHeight, drag:activeDrag};
  }

  function domSnapshot(root){
    const scope = root || document;
    const ghosts = Array.from(document.querySelectorAll('.drag-ghost'));
    const placeholders = Array.from(scope.querySelectorAll('[data-order-drag-placeholder="true"],.order-placeholder'));
    const sources = Array.from(scope.querySelectorAll('[data-drag-order-token].drag-source'));
    const visibleSources = sources.filter(el => {
      const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
      return !style || (style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity || 1) !== 0);
    });
    return {
      ghosts: ghosts.length,
      placeholders: placeholders.length,
      sources: sources.length,
      visibleSources: visibleSources.length,
      bodyDragActive: !!(document.body && document.body.classList && document.body.classList.contains('drag-active'))
    };
  }

  function auditDomSnapshot(snapshot){
    const s = snapshot || {};
    const issues = [];
    if ((s.ghosts || 0) > 1) issues.push('multiple-ghosts');
    if ((s.placeholders || 0) > 1) issues.push('multiple-placeholders');
    if ((s.ghosts || 0) > 0 && (s.visibleSources || 0) > 0) issues.push('visible-source-during-drag');
    if ((s.bodyDragActive || false) && (s.ghosts || 0) === 0) issues.push('drag-active-without-ghost');
    return {ok: issues.length === 0, issues};
  }


  const POINTER_SCHEMA = 'learnit.order_pointer_controller.rc662.v2';

  function orderPointerAvailable(runtime){
    return !!(runtime && runtime.root && runtime.answer && typeof runtime.render === 'function');
  }

  function orderPointerRecord(runtime, event, payload){
    try{
      if(runtime && runtime.journal && typeof runtime.journal.record === 'function'){
        runtime.journal.record(event, Object.assign({module:'LearnItOrderActivity.pointer', pointerSchema:POINTER_SCHEMA}, payload || {}));
      }
    }catch(e){/* no-op */}
  }

  function orderPointerStart(runtime, event, data){
    if(!orderPointerAvailable(runtime) || !event || !data || !data.source) return false;
    if(runtime.drag){
      orderPointerRecord(runtime, 'drag_orphan_recovered', {previousType:runtime.drag.type, newType:data.type});
      if(typeof runtime.cleanupDrag === 'function') runtime.cleanupDrag(true);
    }
    const rect = data.source.getBoundingClientRect();
    const grabX = event.clientX - rect.left;
    const grabY = event.clientY - rect.top;
    const drag = Object.assign({}, data, {
      pointerId:event.pointerId,
      startX:event.clientX,
      startY:event.clientY,
      x:event.clientX,
      y:event.clientY,
      previousY:event.clientY,
      directionY:0,
      moved:false,
      ghost:null,
      raf:0,
      lastDrop:null,
      sourceRect:{width:rect.width, height:rect.height},
      placeholderHeight:Math.ceil(rect.height),
      grabX,
      grabY,
      offsetX:0,
      offsetY:0,
      watchdog:0,
      controller:POINTER_SCHEMA
    });
    runtime.drag = drag;
    try{data.source.setPointerCapture(event.pointerId);}catch(e){/* no-op */}
    drag.watchdog = setTimeout(()=>{
      if(runtime.drag && runtime.drag.pointerId === event.pointerId && runtime.drag.type === 'order'){
        orderPointerRecord(runtime, 'drag_watchdog_cleanup', {type:drag.type, label:drag.label});
        orderPointerCleanup(runtime, true);
      }
    }, 9000);
    orderPointerRecord(runtime, 'direct_drag_start', {type:data.type, label:data.label});
    return true;
  }

  function orderPointerActivate(runtime, drag){
    if(!drag || drag.type !== 'order') return false;
    drag.moved = true;
    runtime.suppressNextClick = true;
    if(drag.source) drag.source.classList.add('drag-source');
    orderPointerCreateGhost(runtime, drag);
    if(document.body) document.body.classList.add('drag-active');
    return true;
  }

  function orderPointerMove(runtime, event){
    const drag = runtime && runtime.drag;
    if(!drag || drag.type !== 'order' || !event || event.pointerId !== drag.pointerId) return false;
    drag.x = event.clientX;
    const previousY = Number.isFinite(drag.y) ? drag.y : event.clientY;
    drag.previousY = previousY;
    drag.y = event.clientY;
    const stepY = drag.y - previousY;
    if(Math.abs(stepY) >= 1) drag.directionY = stepY < 0 ? -1 : 1;
    const dx = drag.x - drag.startX;
    const dy = drag.y - drag.startY;
    if(!drag.moved && Math.hypot(dx, dy) < 4) return true;
    if(!drag.moved) orderPointerActivate(runtime, drag);
    event.preventDefault();
    orderPointerScheduleFrame(runtime, drag);
    orderPointerUpdatePreview(runtime, drag);
    return true;
  }

  function orderPointerCreateGhost(runtime, drag){
    if(!drag || drag.ghost || typeof document === 'undefined') return null;
    const ghost = document.createElement('div');
    ghost.className = 'drag-ghost order-card';
    ghost.textContent = drag.label;
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
    const sourceW = Math.max(1, drag.sourceRect.width || rect.width);
    const sourceH = Math.max(1, drag.sourceRect.height || rect.height);
    drag.offsetX = Math.min(Math.max(drag.grabX * (rect.width / sourceW), 0), rect.width);
    drag.offsetY = Math.min(Math.max(drag.grabY * (rect.height / sourceH), 0), rect.height);
    orderPointerPositionGhost(drag);
    ghost.getBoundingClientRect();
    ghost.style.visibility = 'visible';
    return ghost;
  }

  function orderPointerPositionGhost(drag){
    if(!drag || !drag.ghost) return;
    const x = drag.x - drag.offsetX;
    const y = drag.y - drag.offsetY;
    drag.ghost.style.transform = `translate3d(${x}px,${y}px,0)`;
  }

  function orderPointerScheduleFrame(runtime, drag){
    if(!drag || drag.raf) return;
    drag.raf = requestAnimationFrame(()=>{
      drag.raf = 0;
      orderPointerPositionGhost(drag);
    });
  }

  function orderPointerElementUnderDrag(drag){
    if(!drag || typeof document === 'undefined') return null;
    if(drag.ghost) drag.ghost.style.display = 'none';
    const el = document.elementFromPoint(drag.x, drag.y);
    if(drag.ghost) drag.ghost.style.display = '';
    return el;
  }

  function orderPointerProbeY(drag){
    if(!drag) return 0;
    const height = Math.max(1, Number(drag.sourceRect && drag.sourceRect.height) || Number(drag.placeholderHeight) || 66);
    const offset = Math.max(0, Math.min(Number(drag.offsetY) || 0, height));
    const top = (Number(drag.y) || 0) - offset;
    return top + height / 2;
  }

  function orderPointerComputeIndexFromRects(rects, drag){
    const rows = asArray(rects);
    const probeY = orderPointerProbeY(drag);
    const direction = Number(drag && drag.directionY) || 0;
    /* Direction-aware thresholds make the insertion change earlier in the
       direction of travel. This removes the sticky feeling when lifting a
       card upward while keeping a neutral midpoint when the gesture pauses. */
    const thresholdRatio = direction < 0 ? 0.64 : (direction > 0 ? 0.36 : 0.5);
    for(let i=0;i<rows.length;i+=1){
      const rect = rows[i] || {};
      const top = Number(rect.top) || 0;
      const height = Math.max(1, Number(rect.height) || 1);
      if(probeY < top + height * thresholdRatio) return i;
    }
    return rows.length;
  }

  function orderPointerComputeIndex(runtime, drag){
    const board = runtime && runtime.root ? runtime.root.querySelector('.order-board') : null;
    if(!board) return 0;
    const cards = Array.from(board.querySelectorAll('[data-drag-order-token]')).filter(card => card.dataset.dragOrderToken !== drag.token && !card.classList.contains('drag-source'));
    const rects = cards.map(card => card.getBoundingClientRect());
    return orderPointerComputeIndexFromRects(rects, drag);
  }

  function orderPointerSyncPreviewDom(runtime, drag){
    const board = runtime && runtime.root ? runtime.root.querySelector('.order-board') : null;
    if(!board || !drag) return;
    const placeholders = Array.from(board.querySelectorAll('[data-order-drag-placeholder="true"],.order-placeholder'));
    let placeholder = placeholders[0] || null;
    placeholders.slice(1).forEach(el => el.remove());
    if(drag.overIndex === null || drag.overIndex === undefined){
      if(placeholder) placeholder.remove();
      return;
    }
    if(!placeholder){
      placeholder = document.createElement('div');
      placeholder.className = 'order-placeholder';
      placeholder.setAttribute('aria-hidden', 'true');
    }
    placeholder.dataset.orderDragPlaceholder = 'true';
    placeholder.className = 'order-placeholder';
    placeholder.style.setProperty('--order-placeholder-height', Math.max(48, Math.round(Number(drag.placeholderHeight) || (drag.sourceRect && drag.sourceRect.height) || 66)) + 'px');
    const cards = Array.from(board.querySelectorAll('[data-drag-order-token]')).filter(card => card.dataset.dragOrderToken !== drag.token && !card.classList.contains('drag-source'));
    const before = cards[Math.max(0, Math.min(Number(drag.overIndex) || 0, cards.length))] || null;
    if(before) board.insertBefore(placeholder, before); else board.appendChild(placeholder);
  }

  function orderPointerUpdatePreview(runtime, drag){
    const board = runtime && runtime.root ? runtime.root.querySelector('.order-board') : null;
    if(!board || !drag) return false;
    const el = orderPointerElementUnderDrag(drag);
    const inside = !!(el && el.closest && el.closest('.order-board'));
    if(!inside){
      drag.overIndex = null;
      drag.lastDrop = null;
      orderPointerSyncPreviewDom(runtime, drag);
      return true;
    }
    const next = orderPointerComputeIndex(runtime, drag);
    drag.overIndex = next;
    drag.lastDrop = {type:'order', index:next};
    orderPointerSyncPreviewDom(runtime, drag);
    return true;
  }

  function orderPointerEnd(runtime, event){
    const drag = runtime && runtime.drag;
    if(!drag || drag.type !== 'order' || !event || event.pointerId !== drag.pointerId) return false;
    if(drag.moved) event.preventDefault();
    const drop = drag.lastDrop;
    const moved = drag.moved;
    const token = drag.token;
    orderPointerCleanup(runtime, true);
    if(moved && token && drop && drop.type === 'order') runtime.answer.moveOrderToIndex(token, drop.index);
    return true;
  }

  function orderPointerCancel(runtime, event){
    const drag = runtime && runtime.drag;
    if(!drag || drag.type !== 'order') return false;
    if(event && event.pointerId !== undefined && event.pointerId !== drag.pointerId) return false;
    orderPointerCleanup(runtime, true);
    return true;
  }

  function orderPointerCleanup(runtime, skipRender){
    const drag = runtime && runtime.drag;
    if(!drag || drag.type !== 'order') return false;
    if(drag.watchdog) clearTimeout(drag.watchdog);
    if(drag.raf) cancelAnimationFrame(drag.raf);
    if(drag.ghost) drag.ghost.remove();
    if(drag.source){
      try{
        if(drag.pointerId !== undefined && drag.source.hasPointerCapture && drag.source.hasPointerCapture(drag.pointerId)) drag.source.releasePointerCapture(drag.pointerId);
      }catch(e){/* no-op */}
      drag.source.classList.remove('drag-source');
    }
    if(runtime.root) runtime.root.querySelectorAll('[data-order-drag-placeholder="true"],.order-placeholder').forEach(el => el.remove());
    if(document.body) document.body.classList.remove('drag-active');
    if(runtime && typeof runtime.clearDropHints === 'function') runtime.clearDropHints();
    else if(runtime && runtime.root) runtime.root.querySelectorAll('.hot').forEach(el => el.classList.remove('hot'));
    const needsRender = !!(drag && drag.moved);
    runtime.drag = null;
    if(runtime.suppressNextClick) requestAnimationFrame(()=>{runtime.suppressNextClick = false;});
    if(needsRender && !skipRender && typeof runtime.render === 'function') runtime.render();
    return true;
  }

  const pointer = Object.freeze({
    schema: POINTER_SCHEMA,
    start: orderPointerStart,
    move: orderPointerMove,
    end: orderPointerEnd,
    cancel: orderPointerCancel,
    cleanup: orderPointerCleanup,
    activate: orderPointerActivate,
    createGhost: orderPointerCreateGhost,
    positionGhost: orderPointerPositionGhost,
    scheduleFrame: orderPointerScheduleFrame,
    elementUnderDrag: orderPointerElementUnderDrag,
    computeIndex: orderPointerComputeIndex,
    computeIndexFromRects: orderPointerComputeIndexFromRects,
    probeY: orderPointerProbeY,
    syncPreviewDom: orderPointerSyncPreviewDom,
    updatePreview: orderPointerUpdatePreview
  });

  window.LearnItOrderActivity = Object.freeze({
    schema: 'learnit.order_activity.rc220.v1',
    tokensEqual,
    makeInitial,
    repairPending,
    moveTokenByDelta,
    moveTokenToIndex,
    buildRenderModel,
    domSnapshot,
    auditDomSnapshot,
    pointer
  });
})();
