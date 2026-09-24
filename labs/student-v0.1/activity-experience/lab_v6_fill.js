(()=>{
'use strict';
const {el,emit,stage,header,status,primary,pointerDrag,shuffled}=window.__LAB_CORE__;
const {setPressed,clearPressed,keyActivate,targetAt,clearEligibility,markEligible,markActive}=window.__LAB_V6_HELPERS__;
function fillB(v,p){
  const assignments=new Map(), tokens=new Map(), slots=new Map();
  let selected=null;
  const st=status('Glisse un mot ou sélectionne-le puis touche directement un emplacement mis en évidence.');
  const bankTitle=el('button',{type:'button',class:'fill-bank-title','aria-label':'Mots disponibles — remettre le mot sélectionné dans la banque',text:'Mots disponibles'});const bank=el('section',{class:'fill-b-bank drop-target','data-fill-drop':'bank'},[bankTitle,el('div',{class:'token-bank'})]);
  const bankBox=bank.querySelector('.token-bank'), sentence=el('div',{class:'fill-b-sentence'});
  function tokenLocation(id){for(const[s,t]of assignments)if(t===id)return s;return'bank'}
  function clearDestinationSignals(){clearEligibility(stage)}
  function showDestinations(id){
    clearDestinationSignals();const loc=tokenLocation(id);
    for(const[,slot]of slots)if(!slot.querySelector('.token-chip'))slot.classList.add('eligible-destination');
    if(loc!=='bank')bankTitle.classList.add('eligible-destination')
  }
  function selectToken(id){selected=id;setPressed(tokens,id);showDestinations(id);st.textContent='Mot sélectionné. Les emplacements possibles sont mis en évidence.'}
  function paint(){for(const[,slot]of slots){const filled=!!slot.querySelector('.token-chip');slot.classList.toggle('filled',filled);slot.classList.toggle('empty',!filled);if(filled){slot.removeAttribute('role');slot.removeAttribute('tabindex')}else{slot.setAttribute('role','button');slot.setAttribute('tabindex','0')}}st.textContent=`${assignments.size}/${slots.size} emplacement(s) rempli(s).`}
  function put(tokenId,slotId){const token=tokens.get(tokenId);for(const[s,t]of[...assignments])if(t===tokenId)assignments.delete(s);const old=assignments.get(slotId);if(old&&old!==tokenId)bankBox.append(tokens.get(old));assignments.set(slotId,tokenId);slots.get(slotId).append(token);selected=null;clearPressed(tokens);clearDestinationSignals();paint()}
  function returnBank(tokenId){for(const[s,t]of[...assignments])if(t===tokenId)assignments.delete(s);bankBox.append(tokens.get(tokenId));selected=null;clearPressed(tokens);clearDestinationSignals();paint()}
  bankTitle.addEventListener('click',()=>selected&&returnBank(selected));
  p.segments.forEach(seg=>{if(seg.text)sentence.append(el('span',{text:seg.text}));else{const slot=el('span',{class:'fill-slot empty drop-target','data-fill-drop':seg.slotId,'data-slot-id':seg.slotId,role:'button',tabindex:'0','aria-label':`Emplacement ${seg.slotId}`});slot.addEventListener('click',e=>{if(e.target.closest('.token-chip'))return;if(selected&&!slot.querySelector('.token-chip'))put(selected,seg.slotId)});keyActivate(slot,()=>selected&&!slot.querySelector('.token-chip')&&put(selected,seg.slotId));slots.set(seg.slotId,slot);sentence.append(slot)}});
  shuffled(p.tokens).forEach(t=>{
    const chip=el('button',{type:'button',class:'manip-card drag-card token-chip','data-token-id':t.tokenId,'aria-pressed':'false'},[el('span',{class:'grip','aria-hidden':'true',text:'⠿'}),el('span',{text:t.label})]);
    chip.addEventListener('click',e=>{e.stopPropagation();if(chip.dataset.suppressClick==='true'){chip.dataset.suppressClick='false';return}selectToken(t.tokenId)});
    pointerDrag(chip,{
      onStart:()=>{clearDestinationSignals();chip.classList.add('dragging');const r=chip.getBoundingClientRect();chip.style.width=`${r.width}px`},
      onMove:s=>{chip.style.transform=`translate(${s.x-s.startX}px,${s.y-s.startY}px)`;const hit=targetAt(s.x,s.y,'[data-fill-drop]',chip);markActive(hit?.matches('.fill-slot')?hit:hit?.querySelector('.fill-bank-title')||null)},
      onDrop:s=>{chip.classList.remove('dragging');chip.style.cssText='';markActive(null);clearDestinationSignals();const hit=targetAt(s.x,s.y,'[data-fill-drop]',chip);if(s.moved&&hit){const d=hit.dataset.fillDrop;d==='bank'?returnBank(t.tokenId):put(t.tokenId,d)}if(s.moved){chip.dataset.suppressClick='true';setTimeout(()=>chip.dataset.suppressClick='false',0)}},
      onCancel:()=>{chip.classList.remove('dragging');chip.style.cssText='';markActive(null);clearDestinationSignals()}
    });
    tokens.set(t.tokenId,chip);bankBox.append(chip)
  });
  paint();
  const send=primary('Émettre la réponse',()=>{if(assignments.size!==slots.size){st.textContent='Remplis tous les emplacements.';return}const out={};for(const id of slots.keys())out[id]=assignments.get(id);emit(out)});
  stage.append(header(v,'Candidate : sélectionner un mot révèle les emplacements valides sans modifier la phrase.'),el('p',{text:p.prompt}),bank,sentence,st,el('div',{class:'actions'},[send]))
}


window.__LAB_RENDERERS__['fill-b']=fillB;
})();
