(()=>{
'use strict';
const {el,emit,stage,header,status,primary,pointerDrag,shuffled}=window.__LAB_CORE__;
function flashB(v,p){
  let revealed=false;
  const st=status('Touchez la carte pour voir la réponse.');
  const front=el('div',{class:'flash-face flash-front'},[
    el('div',{class:'flash-section'},[el('span',{class:'small-label',text:'Question'}),el('h3',{text:p.front})])
  ]);
  const back=el('div',{class:'flash-face flash-back'},[
    el('div',{class:'flash-section flash-question-repeat'},[el('span',{class:'small-label',text:'Question'}),el('strong',{text:p.front})]),
    el('div',{class:'flash-section flash-answer'},[el('span',{class:'small-label',text:'Réponse'}),el('strong',{text:p.back})]),
    el('p',{class:'flash-explanation',text:p.explanation})
  ]);
  const inner=el('div',{class:'flash-b-inner'},[front,back]);
  const card=el('button',{type:'button',class:'flash-b-card','aria-label':'Retourner la carte','aria-pressed':'false'},[inner]);
  const cont=primary('Continuer',()=>revealed&&emit({revealed:true})); cont.hidden=true;
  card.onclick=()=>{const toBack=!card.classList.contains('is-back');card.classList.toggle('is-back',toBack);card.setAttribute('aria-pressed',String(toBack));if(toBack){revealed=true;cont.hidden=false;st.textContent='Réponse affichée. La question reste rappelée en haut.'}else st.textContent='Question affichée.'};
  stage.append(header(v,'Candidate : question, réponse et explication suivent le même axe de lecture.'),el('section',{class:'flash-b-shell'},[card,st,el('div',{class:'actions'},[cont])]))
}


window.__LAB_RENDERERS__['flashcard-b']=flashB;
})();
