(()=>{
'use strict';
const {el,emit,stage,header,status,primary,pointerDrag,shuffled}=window.__LAB_CORE__;
const {setPressed,clearPressed,keyActivate,targetAt,clearEligibility,markEligible,markActive}=window.__LAB_V6_HELPERS__;
function matchingB(v,p){
  const map=new Map(), cards=new Map(), rows=new Map();
  let selected=null;
  const leftItems=shuffled(p.leftItems), rightItems=shuffled(p.rightItems);
  const st=status('Glisse une carte vers une description, ou sélectionne-la puis touche une destination mise en évidence.');
  const sourceWrap=el('section',{class:'match-source-wrap'});
  const sourceHead=el('div',{class:'match-source-head'},[el('h3',{text:'Cartes à placer'}),el('span',{class:'muted match-count'})]);
  const source=el('div',{class:'match-source'}), board=el('section',{class:'pair-board'});
  sourceWrap.append(sourceHead,source);
  const targetButtons=()=>[...board.querySelectorAll('.pair-target')];
  function paint(){
    sourceHead.querySelector('.match-count').textContent=`${source.querySelectorAll(':scope > .match-card').length} restante(s)`;
    for(const [rid,row] of rows){const filled=!![...map].find(([,r])=>r===rid);row.classList.toggle('matched',filled);row.querySelector('.pair-slot').classList.toggle('filled',filled)}
    st.textContent=`${map.size}/${p.leftItems.length} association(s).`;
  }
  function clearSelection(){selected=null;clearPressed(cards);clearEligibility(board)}
  function selectCard(id){selected=id;setPressed(cards,id);clearEligibility(board);const current=map.get(id);markEligible(targetButtons().filter(t=>t.dataset.targetId!==current));st.textContent='Carte sélectionnée. Les destinations possibles sont mises en évidence.'}
  function place(lid,rid){
    const slot=rows.get(rid).querySelector('.pair-slot'), incoming=cards.get(lid), occupant=slot.querySelector('.match-card');
    if(occupant&&occupant!==incoming){const old=occupant.dataset.cardId;map.delete(old);source.append(occupant)}
    for(const [k,r] of [...map]) if(k===lid||r===rid) map.delete(k);
    map.set(lid,rid); slot.append(incoming); clearSelection(); paint();
  }
  rightItems.forEach(r=>{
    const slot=el('div',{class:'pair-slot','data-target-id':r.itemId});
    const connector=el('span',{class:'pair-connector','aria-hidden':'true',text:'↔'});
    const target=el('button',{type:'button',class:'pair-target manip-card','data-target-id':r.itemId,text:r.label});
    target.onclick=()=>selected&&place(selected,r.itemId);
    const row=el('div',{class:'pair-row','data-target-id':r.itemId},[slot,connector,target]); rows.set(r.itemId,row); board.append(row);
  });
  leftItems.forEach(i=>{
    const c=el('button',{type:'button',class:'manip-card drag-card match-card','data-card-id':i.itemId,'aria-pressed':'false'},[el('span',{class:'grip','aria-hidden':'true',text:'⠿'}),el('span',{text:i.label})]);
    c.addEventListener('click',e=>{e.stopPropagation();if(c.dataset.suppressClick==='true'){c.dataset.suppressClick='false';return}selectCard(i.itemId)});
    pointerDrag(c,{
      onStart:()=>{clearEligibility(board);c.classList.add('dragging');const r=c.getBoundingClientRect();c.style.width=`${r.width}px`},
      onMove:s=>{c.style.transform=`translate(${s.x-s.startX}px,${s.y-s.startY}px)`;const hit=targetAt(s.x,s.y,'.pair-row',c);markActive(hit?.querySelector('.pair-target')||null)},
      onDrop:s=>{c.classList.remove('dragging');c.style.cssText='';markActive(null);const hit=targetAt(s.x,s.y,'.pair-row',c);if(s.moved&&hit)place(i.itemId,hit.dataset.targetId);else clearEligibility(board);if(s.moved){c.dataset.suppressClick='true';setTimeout(()=>c.dataset.suppressClick='false',0)}},
      onCancel:()=>{c.classList.remove('dragging');c.style.cssText='';markActive(null);clearEligibility(board)}
    });
    cards.set(i.itemId,c); source.append(c);
  });
  paint();
  const send=primary('Émettre la réponse',()=>{if(map.size!==p.leftItems.length){st.textContent='Complète toutes les associations.';return}emit({associations:p.leftItems.map(i=>({leftItemId:i.itemId,rightItemId:map.get(i.itemId)}))})});
  stage.append(header(v,'Candidate : sélectionner un objet révèle les destinations possibles sans déplacer la mise en page.'),el('p',{text:p.prompt}),sourceWrap,board,st,el('div',{class:'actions'},[send]))
}


window.__LAB_RENDERERS__['matching-b']=matchingB;
})();
