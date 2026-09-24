(()=>{
'use strict';
const {el,emit,stage,header,status,primary,pointerDrag,shuffled}=window.__LAB_CORE__;

const setPressed=(map,id)=>map.forEach((node,key)=>node.setAttribute('aria-pressed',String(key===id)));
const clearPressed=map=>map.forEach(node=>node.setAttribute('aria-pressed','false'));
const keyActivate=(node,fn)=>node.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fn(e)}});
const targetAt=(x,y,selector,dragged)=>{for(const node of document.elementsFromPoint(x,y)){const target=node.closest?.(selector);if(target&&(!dragged||!target.contains(dragged)))return target}return null};

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

function matchingB(v,p){
  const map=new Map(), cards=new Map(), rows=new Map();
  let selected=null;
  const leftItems=shuffled(p.leftItems), rightItems=shuffled(p.rightItems);
  const st=status('Glisse une carte vers une description, ou sélectionne-la puis touche la description.');
  const sourceWrap=el('section',{class:'match-source-wrap'});
  const sourceHead=el('div',{class:'match-source-head'},[el('h3',{text:'Cartes à placer'}),el('span',{class:'muted match-count'})]);
  const source=el('div',{class:'match-source'}), board=el('section',{class:'pair-board'});
  sourceWrap.append(sourceHead,source);
  function paint(){
    sourceHead.querySelector('.match-count').textContent=`${source.querySelectorAll(':scope > .match-card').length} restante(s)`;
    for(const [rid,row] of rows){const filled=!![...map].find(([,r])=>r===rid);row.classList.toggle('matched',filled);row.querySelector('.pair-slot').classList.toggle('filled',filled)}
    st.textContent=`${map.size}/${p.leftItems.length} association(s).`;
  }
  function selectCard(id){selected=id;setPressed(cards,id);st.textContent='Carte sélectionnée. Touche une description.'}
  function place(lid,rid){
    const slot=rows.get(rid).querySelector('.pair-slot'), incoming=cards.get(lid), occupant=slot.querySelector('.match-card');
    if(occupant&&occupant!==incoming){const old=occupant.dataset.cardId;map.delete(old);source.append(occupant)}
    for(const [k,r] of [...map]) if(k===lid||r===rid) map.delete(k);
    map.set(lid,rid); slot.append(incoming); selected=null; clearPressed(cards); paint();
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
      onStart:()=>{c.classList.add('dragging');const r=c.getBoundingClientRect();c.style.width=`${r.width}px`},
      onMove:s=>{c.style.transform=`translate(${s.x-s.startX}px,${s.y-s.startY}px)`;board.querySelectorAll('.pair-row').forEach(x=>x.classList.remove('drag-highlight'));targetAt(s.x,s.y,'.pair-row',c)?.classList.add('drag-highlight')},
      onDrop:s=>{c.classList.remove('dragging');c.style.cssText='';board.querySelectorAll('.pair-row').forEach(x=>x.classList.remove('drag-highlight'));const hit=targetAt(s.x,s.y,'.pair-row',c);if(s.moved&&hit)place(i.itemId,hit.dataset.targetId);if(s.moved){c.dataset.suppressClick='true';setTimeout(()=>c.dataset.suppressClick='false',0)}},
      onCancel:()=>{c.classList.remove('dragging');c.style.cssText=''}
    });
    cards.set(i.itemId,c); source.append(c);
  });
  paint();
  const send=primary('Émettre la réponse',()=>{if(map.size!==p.leftItems.length){st.textContent='Complète toutes les associations.';return}emit({associations:p.leftItems.map(i=>({leftItemId:i.itemId,rightItemId:map.get(i.itemId)}))})});
  stage.append(header(v,'Candidate : une cible vide est pointillée ; une fois placée, la carte remplace entièrement cette cible.'),el('p',{text:p.prompt}),sourceWrap,board,st,el('div',{class:'actions'},[send]))
}

function orderB(v,p){
  const list=el('div',{class:'order-b-list',role:'list'}), st=status('Glisse verticalement une étiquette, ou touche-la puis choisis un intercalaire.');
  let selected=null;
  const cards=new Map();
  function cardNodes(){return [...list.querySelectorAll(':scope > .order-b-card')]}
  function clearInsertSlots(){list.querySelectorAll(':scope > .order-insert-slot').forEach(x=>x.remove());list.classList.remove('placing')}
  function clearSelection(){selected=null;clearPressed(cards);clearInsertSlots()}
  function moveSelectedBefore(beforeId){
    if(!selected)return;
    const row=cards.get(selected), before=beforeId?cards.get(beforeId):null;
    if(before===row){clearSelection();return}
    if(before)list.insertBefore(row,before); else list.append(row);
    clearSelection(); st.textContent='Ordre mis à jour.';
  }
  function showInsertSlots(){
    clearInsertSlots(); if(!selected)return;
    list.classList.add('placing');
    const nodes=cardNodes();
    for(const node of nodes){
      const slot=el('button',{type:'button',class:'order-insert-slot','data-before-id':node.dataset.id,'aria-label':`Placer avant ${node.querySelector('.order-b-label').textContent}`},[el('span',{class:'order-insert-line','aria-hidden':'true'})]);
      slot.onclick=()=>moveSelectedBefore(node.dataset.id); list.insertBefore(slot,node);
    }
    const end=el('button',{type:'button',class:'order-insert-slot order-insert-end','data-before-id':'','aria-label':'Placer à la fin'},[el('span',{class:'order-insert-line','aria-hidden':'true'})]);
    end.onclick=()=>moveSelectedBefore(null); list.append(end);
  }
  function selectRow(row){
    selected=row.dataset.id; setPressed(cards,selected); showInsertSlots(); st.textContent='Étiquette sélectionnée. Touche un intercalaire pour la placer.';
  }
  shuffled(p.items).forEach(i=>{
    const row=el('div',{class:'manip-card order-b-card drag-card',role:'button',tabindex:'0','data-id':i.itemId,'aria-pressed':'false','aria-label':`${i.label}. Toucher pour choisir une position.`},[el('span',{class:'grip','aria-hidden':'true',text:'⠿'}),el('span',{class:'order-b-label',text:i.label})]);
    row.addEventListener('click',()=>{if(row.dataset.suppressClick==='true'){row.dataset.suppressClick='false';return}selectRow(row)});
    keyActivate(row,()=>selectRow(row));
    pointerDrag(row,{
      onStart:(s,e)=>{
        const r=row.getBoundingClientRect();
        s.offsetY=e.clientY-r.top;s.fixedLeft=r.left;s.width=r.width;s.height=r.height;s.active=false;
      },
      onMove:s=>{
        if(!s.moved)return;
        if(!s.active){
          s.active=true;clearSelection();
          const placeholder=el('div',{class:'order-placeholder','aria-hidden':'true'});placeholder.style.height=`${s.height}px`;s.placeholder=placeholder;list.insertBefore(placeholder,row);
          const ghost=row.cloneNode(true);ghost.classList.remove('drag-card');ghost.classList.add('order-ghost');ghost.removeAttribute('tabindex');ghost.setAttribute('aria-hidden','true');ghost.style.left=`${s.fixedLeft}px`;ghost.style.top=`${s.startY-s.offsetY}px`;ghost.style.width=`${s.width}px`;ghost.style.height=`${s.height}px`;document.body.append(ghost);s.ghost=ghost;
          row.classList.add('drag-source');row.style.height='0px';row.style.minHeight='0px';row.style.paddingTop='0';row.style.paddingBottom='0';row.style.borderWidth='0';row.style.margin='0';row.style.overflow='hidden';
          st.textContent='Déplacement vertical en cours.';
        }
        s.ghost.style.left=`${s.fixedLeft}px`;s.ghost.style.top=`${s.y-s.offsetY}px`;
        const others=cardNodes().filter(x=>x!==row);
        let placed=false;
        for(const other of others){const r=other.getBoundingClientRect();if(s.y<r.top+r.height/2){list.insertBefore(s.placeholder,other);placed=true;break}}
        if(!placed)list.append(s.placeholder);
      },
      onDrop:s=>{
        if(!s.active)return;
        s.ghost?.remove();
        if(s.placeholder){list.insertBefore(row,s.placeholder);s.placeholder.remove()}
        row.classList.remove('drag-source');row.style.cssText='';
        row.dataset.suppressClick='true';setTimeout(()=>row.dataset.suppressClick='false',0);
        st.textContent='Ordre mis à jour.';
      },
      onCancel:s=>{
        if(!s.active)return;
        s.ghost?.remove();s.placeholder?.remove();row.classList.remove('drag-source');row.style.cssText='';st.textContent='Déplacement annulé.';
      }
    });
    cards.set(i.itemId,row);list.append(row);
  });
  const send=primary('Émettre la réponse',()=>emit({orderedItemIds:cardNodes().map(x=>x.dataset.id)}));
  stage.append(header(v,'Candidate : déplacement strictement vertical avec espace d’insertion, plus intercalaires tactiles sans glisser.'),el('p',{text:p.prompt}),el('p',{class:'order-b-help',text:'La poignée ⠿ est seulement un indice visuel : toute l’étiquette peut être saisie.'}),list,st,el('div',{class:'actions'},[send]))
}

function classifyB(v,p){
  const values=new Map(p.items.map(i=>[i.itemId,''])), cards=new Map(), buckets=new Map();
  let selected=null;
  const st=status('Glisse une carte ou sélectionne-la puis touche directement une catégorie.');
  const sourceTitle=el('button',{type:'button',class:'bucket-title classify-destination','data-dest':'source',text:'À classer'});const source=el('section',{class:'classify-source drop-target','data-drop-zone':'source'},[sourceTitle,el('div',{class:'classify-source-cards'})]);
  const sourceCards=source.querySelector('.classify-source-cards'), grid=el('section',{class:'bucket-grid'});
  function selectCard(id){selected=id;setPressed(cards,id);st.textContent='Carte sélectionnée. Touche une catégorie.'}
  function paint(){for(const[,b]of buckets)b.classList.toggle('empty',b.querySelector('.bucket-cards').children.length===0);source.classList.toggle('empty',sourceCards.children.length===0);st.textContent=`${[...values.values()].filter(Boolean).length}/${p.items.length} carte(s) classée(s).`}
  function moveCard(id,dest){const card=cards.get(id);if(dest==='source'){values.set(id,'');sourceCards.append(card)}else{values.set(id,dest);buckets.get(dest).querySelector('.bucket-cards').append(card)}selected=null;clearPressed(cards);paint()}
  function activateDestination(dest){if(selected)moveCard(selected,dest)}
  sourceTitle.addEventListener('click',()=>activateDestination('source'));
  p.buckets.forEach(b=>{const cardsBox=el('div',{class:'bucket-cards'}),title=el('button',{type:'button',class:'bucket-title classify-destination','data-dest':b.bucketId,text:b.label}),bucket=el('section',{class:'bucket drop-target empty','data-drop-zone':b.bucketId},[title,cardsBox]);title.addEventListener('click',()=>activateDestination(b.bucketId));buckets.set(b.bucketId,bucket);grid.append(bucket)});
  shuffled(p.items).forEach(i=>{
    const card=el('button',{type:'button',class:'manip-card drag-card classify-card','data-card-id':i.itemId,'aria-pressed':'false'},[el('span',{class:'grip','aria-hidden':'true',text:'⠿'}),el('span',{class:'label',text:i.label})]);
    card.addEventListener('click',e=>{e.stopPropagation();if(card.dataset.suppressClick==='true'){card.dataset.suppressClick='false';return}selectCard(i.itemId)});
    pointerDrag(card,{
      onStart:()=>{card.classList.add('dragging');const r=card.getBoundingClientRect();card.style.width=`${r.width}px`},
      onMove:s=>{card.style.transform=`translate(${s.x-s.startX}px,${s.y-s.startY}px)`;document.querySelectorAll('[data-drop-zone]').forEach(x=>x.classList.remove('drag-highlight'));targetAt(s.x,s.y,'[data-drop-zone]',card)?.classList.add('drag-highlight')},
      onDrop:s=>{card.classList.remove('dragging');card.style.cssText='';document.querySelectorAll('[data-drop-zone]').forEach(x=>x.classList.remove('drag-highlight'));const hit=targetAt(s.x,s.y,'[data-drop-zone]',card);if(s.moved&&hit)moveCard(i.itemId,hit.dataset.dropZone);if(s.moved){card.dataset.suppressClick='true';setTimeout(()=>card.dataset.suppressClick='false',0)}},
      onCancel:()=>{card.classList.remove('dragging');card.style.cssText=''}
    });
    cards.set(i.itemId,card);sourceCards.append(card)
  });
  paint();
  const send=primary('Émettre la réponse',()=>{if([...values.values()].some(x=>!x)){st.textContent='Classe toutes les cartes avant de continuer.';return}emit({assignments:p.items.map(i=>({itemId:i.itemId,bucketId:values.get(i.itemId)}))})});
  stage.append(header(v,'Candidate : sélectionner une carte puis toucher directement un bucket suffit ; aucun panneau intermédiaire.'),el('p',{text:p.prompt}),source,grid,st,el('div',{class:'actions'},[send]))
}

function fillB(v,p){
  const assignments=new Map(), tokens=new Map(), slots=new Map();
  let selected=null;
  const st=status('Glisse un mot ou sélectionne-le puis touche directement un emplacement.');
  const bankTitle=el('button',{type:'button',class:'fill-bank-title','aria-label':'Mots disponibles — remettre le mot sélectionné dans la banque',text:'Mots disponibles'});const bank=el('section',{class:'fill-b-bank drop-target','data-fill-drop':'bank'},[bankTitle,el('div',{class:'token-bank'})]);
  const bankBox=bank.querySelector('.token-bank'), sentence=el('div',{class:'fill-b-sentence'});
  function selectToken(id){selected=id;setPressed(tokens,id);st.textContent='Mot sélectionné. Touche un emplacement.'}
  function paint(){for(const[,slot]of slots){const filled=!!slot.querySelector('.token-chip');slot.classList.toggle('filled',filled);slot.classList.toggle('empty',!filled);if(filled){slot.removeAttribute('role');slot.removeAttribute('tabindex')}else{slot.setAttribute('role','button');slot.setAttribute('tabindex','0')}}st.textContent=`${assignments.size}/${slots.size} emplacement(s) rempli(s).`}
  function put(tokenId,slotId){const token=tokens.get(tokenId);for(const[s,t]of[...assignments])if(t===tokenId)assignments.delete(s);const old=assignments.get(slotId);if(old&&old!==tokenId)bankBox.append(tokens.get(old));assignments.set(slotId,tokenId);slots.get(slotId).append(token);selected=null;clearPressed(tokens);paint()}
  function returnBank(tokenId){for(const[s,t]of[...assignments])if(t===tokenId)assignments.delete(s);bankBox.append(tokens.get(tokenId));selected=null;clearPressed(tokens);paint()}
  bankTitle.addEventListener('click',()=>selected&&returnBank(selected));
  p.segments.forEach(seg=>{if(seg.text)sentence.append(el('span',{text:seg.text}));else{const slot=el('span',{class:'fill-slot empty drop-target','data-fill-drop':seg.slotId,'data-slot-id':seg.slotId,role:'button',tabindex:'0','aria-label':`Emplacement ${seg.slotId}`});slot.addEventListener('click',e=>{if(e.target.closest('.token-chip'))return;if(selected&&!slot.querySelector('.token-chip'))put(selected,seg.slotId)});keyActivate(slot,()=>selected&&!slot.querySelector('.token-chip')&&put(selected,seg.slotId));slots.set(seg.slotId,slot);sentence.append(slot)}});
  shuffled(p.tokens).forEach(t=>{
    const chip=el('button',{type:'button',class:'manip-card drag-card token-chip','data-token-id':t.tokenId,'aria-pressed':'false'},[el('span',{class:'grip','aria-hidden':'true',text:'⠿'}),el('span',{text:t.label})]);
    chip.addEventListener('click',e=>{e.stopPropagation();if(chip.dataset.suppressClick==='true'){chip.dataset.suppressClick='false';return}selectToken(t.tokenId)});
    pointerDrag(chip,{
      onStart:()=>{chip.classList.add('dragging');const r=chip.getBoundingClientRect();chip.style.width=`${r.width}px`},
      onMove:s=>{chip.style.transform=`translate(${s.x-s.startX}px,${s.y-s.startY}px)`;document.querySelectorAll('[data-fill-drop]').forEach(x=>x.classList.remove('drag-highlight'));targetAt(s.x,s.y,'[data-fill-drop]',chip)?.classList.add('drag-highlight')},
      onDrop:s=>{chip.classList.remove('dragging');chip.style.cssText='';document.querySelectorAll('[data-fill-drop]').forEach(x=>x.classList.remove('drag-highlight'));const hit=targetAt(s.x,s.y,'[data-fill-drop]',chip);if(s.moved&&hit){const d=hit.dataset.fillDrop;d==='bank'?returnBank(t.tokenId):put(t.tokenId,d)}if(s.moved){chip.dataset.suppressClick='true';setTimeout(()=>chip.dataset.suppressClick='false',0)}},
      onCancel:()=>{chip.classList.remove('dragging');chip.style.cssText=''}
    });
    tokens.set(t.tokenId,chip);bankBox.append(chip)
  });
  paint();
  const send=primary('Émettre la réponse',()=>{if(assignments.size!==slots.size){st.textContent='Remplis tous les emplacements.';return}const out={};for(const id of slots.keys())out[id]=assignments.get(id);emit(out)});
  stage.append(header(v,'Candidate : sélectionner un mot puis toucher directement un emplacement suffit ; un slot rempli n’ajoute aucun second cadre.'),el('p',{text:p.prompt}),bank,sentence,st,el('div',{class:'actions'},[send]))
}

Object.assign(window.__LAB_RENDERERS__,{'flashcard-b':flashB,'matching-b':matchingB,'order-b':orderB,'classify-b':classifyB,'fill-b':fillB});
})();
