(()=>{
'use strict';
const {el,emit,stage,header,status,primary,pointerDrag,shuffled}=window.__LAB_CORE__;
const {setPressed,clearPressed,keyActivate,targetAt,clearEligibility,markEligible,markActive}=window.__LAB_V6_HELPERS__;
function orderB(v,p){
  const list=el('div',{class:'order-b-list',role:'list'}), st=status('Glisse verticalement une étiquette, ou touche-la puis choisis un intercalaire superposé.');
  const overlay=el('div',{class:'order-insert-overlay','aria-hidden':'true'});
  list.append(overlay);
  let selected=null;
  const cards=new Map();
  function cardNodes(){return [...list.querySelectorAll(':scope > .order-b-card')]}
  function clearOverlay(){overlay.replaceChildren();overlay.classList.remove('visible');overlay.setAttribute('aria-hidden','true');list.classList.remove('placing')}
  function clearSelection(){selected=null;clearPressed(cards);clearOverlay()}
  function moveSelectedBefore(beforeId){
    if(!selected)return;
    const row=cards.get(selected), before=beforeId?cards.get(beforeId):null;
    if(before===row){clearSelection();return}
    if(before)list.insertBefore(row,before); else list.insertBefore(row,overlay);
    clearSelection(); st.textContent='Ordre mis à jour.';
  }
  function makeSlot(top,beforeId,label){
    const slot=el('button',{type:'button',class:'order-insert-slot eligible-destination','data-before-id':beforeId||'','aria-label':label},[el('span',{class:'order-insert-line','aria-hidden':'true'})]);
    slot.style.top=`${top}px`;slot.onclick=()=>moveSelectedBefore(beforeId);overlay.append(slot)
  }
  function showInsertOverlay(){
    clearOverlay(); if(!selected)return;
    const nodes=cardNodes(); if(!nodes.length)return;
    const listRect=list.getBoundingClientRect(), rects=nodes.map(n=>n.getBoundingClientRect());
    makeSlot(rects[0].top-listRect.top,nodes[0].dataset.id,`Placer avant ${nodes[0].querySelector('.order-b-label').textContent}`);
    for(let i=1;i<nodes.length;i++){
      const y=((rects[i-1].bottom+rects[i].top)/2)-listRect.top;
      makeSlot(y,nodes[i].dataset.id,`Placer avant ${nodes[i].querySelector('.order-b-label').textContent}`)
    }
    makeSlot(rects.at(-1).bottom-listRect.top,null,'Placer à la fin');
    const slots=[...overlay.querySelectorAll('.order-insert-slot')];
    if(slots.length){slots[0].dataset.position='start';slots.at(-1).dataset.position='end'}
    overlay.classList.add('visible');overlay.setAttribute('aria-hidden','false');list.classList.add('placing')
  }
  function selectRow(row){selected=row.dataset.id;setPressed(cards,selected);showInsertOverlay();st.textContent='Étiquette sélectionnée. Les intercalaires indiquent les positions possibles.'}
  shuffled(p.items).forEach(i=>{
    const row=el('div',{class:'manip-card order-b-card drag-card',role:'button',tabindex:'0','data-id':i.itemId,'aria-pressed':'false','aria-label':`${i.label}. Toucher pour choisir une position.`},[el('span',{class:'grip','aria-hidden':'true',text:'⠿'}),el('span',{class:'order-b-label',text:i.label})]);
    row.addEventListener('click',()=>{if(row.dataset.suppressClick==='true'){row.dataset.suppressClick='false';return}selectRow(row)});
    keyActivate(row,()=>selectRow(row));
    pointerDrag(row,{
      onStart:(s,e)=>{const r=row.getBoundingClientRect();s.offsetY=e.clientY-r.top;s.fixedLeft=r.left;s.width=r.width;s.height=r.height;s.active=false},
      onMove:s=>{
        if(!s.moved)return;
        if(!s.active){
          s.active=true;clearSelection();
          const placeholder=el('div',{class:'order-placeholder active-destination','aria-hidden':'true'});placeholder.style.height=`${s.height}px`;s.placeholder=placeholder;list.insertBefore(placeholder,row);
          const ghost=row.cloneNode(true);ghost.classList.remove('drag-card');ghost.classList.add('order-ghost','dragging');ghost.removeAttribute('tabindex');ghost.setAttribute('aria-hidden','true');ghost.style.left=`${s.fixedLeft}px`;ghost.style.top=`${s.startY-s.offsetY}px`;ghost.style.width=`${s.width}px`;ghost.style.height=`${s.height}px`;document.body.append(ghost);s.ghost=ghost;
          row.classList.add('drag-source');row.style.height='0px';row.style.minHeight='0px';row.style.paddingTop='0';row.style.paddingBottom='0';row.style.borderWidth='0';row.style.margin='0';row.style.overflow='hidden';
          st.textContent='Déplacement vertical en cours.';
        }
        s.ghost.style.left=`${s.fixedLeft}px`;s.ghost.style.top=`${s.y-s.offsetY}px`;
        const others=cardNodes().filter(x=>x!==row);let placed=false;
        for(const other of others){const r=other.getBoundingClientRect();if(s.y<r.top+r.height/2){list.insertBefore(s.placeholder,other);placed=true;break}}
        if(!placed)list.insertBefore(s.placeholder,overlay)
      },
      onDrop:s=>{
        if(!s.active)return;
        s.ghost?.remove();if(s.placeholder){list.insertBefore(row,s.placeholder);s.placeholder.remove()}
        row.classList.remove('drag-source');row.style.cssText='';row.dataset.suppressClick='true';setTimeout(()=>row.dataset.suppressClick='false',0);st.textContent='Ordre mis à jour.'
      },
      onCancel:s=>{if(!s.active)return;s.ghost?.remove();s.placeholder?.remove();row.classList.remove('drag-source');row.style.cssText='';st.textContent='Déplacement annulé.'}
    });
    cards.set(i.itemId,row);list.insertBefore(row,overlay)
  });
  const send=primary('Émettre la réponse',()=>emit({orderedItemIds:cardNodes().map(x=>x.dataset.id)}));
  stage.append(header(v,'Candidate : les intercalaires sont superposés et ne déplacent jamais les étiquettes lors de la sélection.'),el('p',{text:p.prompt}),el('p',{class:'order-b-help',text:'La poignée ⠿ est seulement un indice visuel : toute l’étiquette peut être saisie.'}),list,st,el('div',{class:'actions'},[send]))
}


window.__LAB_RENDERERS__['order-b']=orderB;
})();
