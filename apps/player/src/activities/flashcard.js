(function(){
  'use strict';

  function answerText(activity){
    return String((activity && (activity.answer || activity.back)) || '');
  }

  function makeInitial(){
    return {revealed:false, grade:null};
  }

  function normalizePending(pending){
    const p = pending && typeof pending === 'object' ? pending : {};
    return {revealed:!!p.revealed, grade:typeof p.grade === 'boolean' ? p.grade : null};
  }

  function reveal(pending){
    const p = normalizePending(pending);
    if(p.revealed) return {changed:false, pending:p};
    p.revealed = true;
    return {changed:true, pending:p};
  }

  function grade(activity, pending, correct){
    const ok = !!correct;
    const p = normalizePending(pending);
    p.revealed = true;
    p.grade = ok;
    return {
      pending:p,
      feedback:{
        correct:ok,
        expected:answerText(activity),
        why:(activity && activity.why) || answerText(activity),
        remediation:(activity && activity.remediation) || 'Marque cette carte à revoir puis relis la définition.'
      }
    };
  }

  function expectedText(activity){
    return answerText(activity);
  }

  function isRevealed(pending){
    return normalizePending(pending).revealed;
  }

  function domSnapshot(root){
    const scope = root || document;
    const board = scope.querySelector('[data-activity-type="flashcard"]') || scope;
    const revealButtons = Array.from(board.querySelectorAll('[data-action="flashcard-reveal"]'));
    const gradeButtons = Array.from(board.querySelectorAll('[data-action="flashcard-grade"]'));
    return {
      frontFaces: board.querySelectorAll('.flashcard-face.front').length,
      backFaces: board.querySelectorAll('.flashcard-face.back').length,
      revealButtons: revealButtons.length,
      gradeButtons: gradeButtons.length,
      revealed: board.getAttribute('data-flashcard-revealed') === 'true',
      focusableActions: revealButtons.concat(gradeButtons).filter(el => el.tagName === 'BUTTON').length
    };
  }

  function auditDomSnapshot(snapshot){
    const s = snapshot || {};
    const issues = [];
    if((s.frontFaces || 0) !== 1) issues.push('flashcard-front-face-missing-or-duplicated');
    if(s.revealed && (s.backFaces || 0) !== 1) issues.push('flashcard-revealed-without-single-back-face');
    if(!s.revealed && (s.backFaces || 0) > 0) issues.push('flashcard-back-visible-before-reveal');
    if(!s.revealed && (s.revealButtons || 0) !== 1) issues.push('flashcard-reveal-button-missing');
    if(s.revealed && (s.gradeButtons || 0) !== 2) issues.push('flashcard-grade-buttons-missing');
    if((s.revealButtons || 0) + (s.gradeButtons || 0) !== (s.focusableActions || 0)) issues.push('non-focusable-flashcard-action');
    return {ok:issues.length === 0, issues};
  }

  window.LearnItFlashcardActivity = Object.freeze({
    schema:'learnit.flashcard_activity.rc223.v1',
    makeInitial,
    normalizePending,
    reveal,
    grade,
    expectedText,
    isRevealed,
    domSnapshot,
    auditDomSnapshot
  });
})();
