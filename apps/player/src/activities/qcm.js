(function(){
  'use strict';

  function choices(activity){
    return Array.isArray(activity && activity.choices) ? activity.choices.slice() : [];
  }

  function answerIndex(activity){
    const n = Number(activity && activity.answer);
    return Number.isInteger(n) ? n : -1;
  }

  function normalizePending(activity, pending){
    if(pending === null || pending === undefined || pending === '' || typeof pending === 'boolean') return null;
    const i = Number(pending);
    return Number.isInteger(i) && i >= 0 && i < choices(activity).length ? i : null;
  }

  function makeInitial(){
    return null;
  }

  function selectChoice(activity, pending, index){
    const previous = normalizePending(activity, pending);
    const next = normalizePending(activity, index);
    if(next === null) return {changed:false, pending:previous, selectedIndex:previous, reason:'invalid-choice-index'};
    return {changed:previous !== next, pending:next, selectedIndex:next, previousIndex:previous};
  }

  function isComplete(activity, pending){
    return normalizePending(activity, pending) !== null;
  }

  function isCorrect(activity, pending){
    return normalizePending(activity, pending) === answerIndex(activity);
  }

  function expectedText(activity){
    const a = answerIndex(activity);
    const cs = choices(activity);
    return a >= 0 && a < cs.length ? String(cs[a]) : '';
  }

  function choiceStates(activity, pending, locked){
    const selected = normalizePending(activity, pending);
    const answer = answerIndex(activity);
    return choices(activity).map((choice, index) => ({
      choice,
      index,
      selected: selected === index,
      correct: !!locked && index === answer,
      wrong: !!locked && selected === index && selected !== answer
    }));
  }

  function domSnapshot(root){
    const scope = root || document;
    const board = scope.querySelector('[data-activity-type="qcm"]') || scope;
    const choiceEls = Array.from(board.querySelectorAll('[data-qcm-choice]'));
    const selectedEls = choiceEls.filter(el => el.classList.contains('selected') || el.getAttribute('aria-pressed') === 'true' || el.getAttribute('aria-checked') === 'true');
    const disabledEls = choiceEls.filter(el => el.disabled || el.getAttribute('disabled') !== null);
    return {
      choices: choiceEls.length,
      selected: selectedEls.length,
      disabled: disabledEls.length,
      focusableChoices: choiceEls.filter(el => el.tagName === 'BUTTON').length,
      hasAnswerPanel: !!board.querySelector('.activity-answer-panel')
    };
  }

  function auditDomSnapshot(snapshot){
    const s = snapshot || {};
    const issues = [];
    if((s.choices || 0) < 2) issues.push('qcm-too-few-choices');
    if((s.selected || 0) > 1) issues.push('multiple-selected-qcm-choices');
    if((s.choices || 0) !== (s.focusableChoices || 0)) issues.push('non-focusable-qcm-choice');
    if(!s.hasAnswerPanel) issues.push('missing-qcm-answer-panel');
    return {ok:issues.length === 0, issues};
  }

  window.LearnItQcmActivity = Object.freeze({
    schema:'learnit.qcm_activity.rc223.v1',
    makeInitial,
    normalizePending,
    selectChoice,
    isComplete,
    isCorrect,
    expectedText,
    choiceStates,
    domSnapshot,
    auditDomSnapshot
  });
})();
