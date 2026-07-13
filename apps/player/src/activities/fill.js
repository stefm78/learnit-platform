(function(){
  'use strict';

  function asArray(value){
    return Array.isArray(value) ? value : [];
  }

  function answerLength(activity){
    return asArray(activity && activity.answer).length;
  }

  function tokens(activity){
    return asArray(activity && activity.tokens).slice();
  }

  function count(values){
    const m = new Map();
    asArray(values).forEach(v => m.set(v, (m.get(v) || 0) + 1));
    return m;
  }

  function tokenCapacities(activity){
    const declared = count(tokens(activity));
    const required = count(asArray(activity && activity.answer));
    const capacity = new Map(declared);
    for(const [token, needed] of required.entries()){
      capacity.set(token, Math.max(capacity.get(token) || 0, needed));
    }
    return capacity;
  }

  function effectiveTokens(activity){
    const ordered = [];
    const seen = new Set();
    tokens(activity).concat(asArray(activity && activity.answer)).forEach(token => {
      if(!seen.has(token)){
        seen.add(token);
        ordered.push(token);
      }
    });
    return ordered;
  }

  function makeInitial(activity){
    return Array(answerLength(activity)).fill('');
  }

  function normalizePending(activity, pending){
    const size = answerLength(activity);
    const values = asArray(pending).slice(0, size);
    while(values.length < size) values.push('');
    const bankCounts = tokenCapacities(activity);
    const used = new Map();
    for(let i = 0; i < values.length; i += 1){
      const value = values[i];
      if(!value) continue;
      const capacity = bankCounts.get(value) || 0;
      const current = used.get(value) || 0;
      if(capacity <= 0 || current >= capacity) values[i] = '';
      else used.set(value, current + 1);
    }
    return values;
  }

  function nextEmptyIndex(values, fromIndex){
    const arr = asArray(values);
    const start = Math.max(0, Math.min(Number(fromIndex || 0), arr.length));
    for(let i = start; i < arr.length; i += 1) if(!arr[i]) return i;
    for(let i = 0; i < start; i += 1) if(!arr[i]) return i;
    return -1;
  }

  function tokenUsage(activity, pending){
    const values = normalizePending(activity, pending);
    const usage = count(values.filter(Boolean));
    const capacity = tokenCapacities(activity);
    const out = {};
    effectiveTokens(activity).forEach(token => {
      out[token] = {used:usage.get(token) || 0, capacity:capacity.get(token) || 0};
    });
    return out;
  }

  function isTokenAvailable(activity, pending, token){
    const usage = tokenUsage(activity, pending)[token];
    if(!usage) return false;
    return usage.used < usage.capacity;
  }

  function placeToken(activity, pending, token, selectedIndex){
    const values = normalizePending(activity, pending);
    if(!isTokenAvailable(activity, values, token)){
      return {changed:false, values, placedIndex:-1, nextSelectedIndex:nextEmptyIndex(values, 0), reason:'token-unavailable'};
    }
    let index = Number.isInteger(selectedIndex) ? selectedIndex : -1;
    if(index < 0 || index >= values.length || values[index]) index = nextEmptyIndex(values, 0);
    if(index < 0) return {changed:false, values, placedIndex:-1, nextSelectedIndex:-1, reason:'no-empty-slot'};
    values[index] = token;
    const next = nextEmptyIndex(values, index + 1);
    return {changed:true, values, placedIndex:index, nextSelectedIndex:next};
  }

  function clearIndex(activity, pending, index){
    const values = normalizePending(activity, pending);
    const i = Number(index);
    if(!Number.isInteger(i) || i < 0 || i >= values.length) return {changed:false, values, cleared:null};
    const cleared = values[i] || null;
    if(!cleared) return {changed:false, values, cleared:null};
    values[i] = '';
    return {changed:true, values, cleared, nextSelectedIndex:i};
  }

  function isComplete(activity, pending){
    const values = normalizePending(activity, pending);
    return values.length === answerLength(activity) && values.every(Boolean);
  }

  function isCorrect(activity, pending){
    const values = normalizePending(activity, pending);
    return JSON.stringify(values) === JSON.stringify(asArray(activity && activity.answer));
  }

  function expectedText(activity){
    return String((activity && activity.sentence) || asArray(activity && activity.answer).join(' '));
  }

  function tokenStates(activity, pending){
    const usage = tokenUsage(activity, pending);
    return effectiveTokens(activity).map((token, index) => {
      const u = usage[token] || {used:0, capacity:0};
      const remainingCount = Math.max(0, u.capacity - u.used);
      return {token, index, used:u.used >= u.capacity && u.capacity > 0, usedCount:u.used, capacity:u.capacity, remainingCount, reusable:u.capacity > 1};
    });
  }

  function domSnapshot(root){
    const scope = root || document;
    const board = scope.querySelector('[data-activity-type="fill"]') || scope;
    const slots = Array.from(board.querySelectorAll('[data-fill-slot]'));
    const selectedSlots = slots.filter(el => el.classList.contains('selected') || el.getAttribute('aria-selected') === 'true');
    const emptySlots = slots.filter(el => el.classList.contains('empty'));
    const tokensEls = Array.from(board.querySelectorAll('[data-fill-token]'));
    const usedTokens = tokensEls.filter(el => el.classList.contains('used') || el.getAttribute('aria-disabled') === 'true');
    const nativeInputs = Array.from(board.querySelectorAll('input,textarea,[contenteditable="true"]'));
    return {
      slots: slots.length,
      emptySlots: emptySlots.length,
      selectedSlots: selectedSlots.length,
      tokens: tokensEls.length,
      usedTokens: usedTokens.length,
      nativeInputs: nativeInputs.length,
      focusableSlots: slots.filter(el => el.tagName === 'BUTTON').length,
      focusableTokens: tokensEls.filter(el => el.tagName === 'BUTTON').length
    };
  }

  function auditDomSnapshot(snapshot){
    const s = snapshot || {};
    const issues = [];
    if((s.selectedSlots || 0) > 1) issues.push('multiple-selected-fill-slots');
    if((s.slots || 0) !== (s.focusableSlots || 0)) issues.push('non-focusable-fill-slot');
    if((s.tokens || 0) !== (s.focusableTokens || 0)) issues.push('non-focusable-fill-token');
    if((s.nativeInputs || 0) > 0) issues.push('unexpected-mobile-keyboard-input');
    return {ok:issues.length === 0, issues};
  }

  window.LearnItFillActivity = Object.freeze({
    schema:'learnit.fill_activity.rc661.v2',
    tokenCapacities,
    effectiveTokens,
    makeInitial,
    normalizePending,
    nextEmptyIndex,
    tokenUsage,
    tokenStates,
    isTokenAvailable,
    placeToken,
    clearIndex,
    isComplete,
    isCorrect,
    expectedText,
    domSnapshot,
    auditDomSnapshot
  });
})();
