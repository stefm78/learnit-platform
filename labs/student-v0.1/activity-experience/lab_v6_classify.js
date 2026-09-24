(()=>{
'use strict';
const {el,emit,stage,header,status,primary,pointerDrag,shuffled}=window.__LAB_CORE__;
const {setPressed,clearPressed,keyActivate,targetAt,clearEligibility,markEligible,markActive}=window.__LAB_V6_HELPERS__;
function classifyB(v,p){
  const values=new Map(p.items.map(i=>[i.itemId,''])), cards=new Map(), buckets=new Map();
  let selected=null;
  const st=status('Glisse une carte ou sélectionne-la puis touche directement une catégorie mise en évidence.');
  const sourceTitle=el('button',{type:'button',class:'bucket-title classify-destination','data-dest':'source',text:'À classer'});const source=el('section',{class:'classify-source drop-target','data-drop-zone':'source'},[sourceTitle,el('div',{class:'classify-source-cards'})]);
  const sourceCards=source.querySelector('.classify-source-cards'), grid=el('section',{class:'bucket-grid'});
  function currentDest(id){return values.get(id)||'source'}
  function clearDestinationSignals(){clearEligibility(stage)}
  function showDestinations(id){
    clearDestinationSignals();const current=currentDest(id);
    if(current!=='source'){sourceTitle.classList.add('eligible-destination');source.classList.add('eligible-zone')}
    for(const [bid,b] of buckets)if(bid!==current){b.querySelector('.classify-destination').classList.add('eligible-destination');b.classList.add('eligible-zone')}
  }
  function selectCard(id){selected=id;setPressed(cards,id);showDestinations(id);st.textContent='Carte sélectionnée. Les catégories possibles sont mises en évidence.'}
  function paint(){for(const[,b]of buckets)b.classList.toggle('empty',b.querySelector('.bucket-cards').children.length===0);source.classList.toggle('empty',sourceCards.children.length===0);st.textContent=`${[...values.values()].filter(Boolean).length}/${p.items.length} carte(s) classée(s).`}
  function moveCard(id,dest){const card=cards.get(id);if(dest==='source'){values.set(id,'');sourceCards.append(card)}else{values.set(id,dest);buckets.get(dest).querySelector('.bucket-cards').append(card)}selected=null;clearPressed(cards);clearDestinationSignals();paint()}
  function activateDestination(dest){if(selected&&dest!==currentDest(selected))moveCard(selected,dest)}
  sourceTitle.addEventListener('click',()=>activateDestination('source'));
  p.buckets.forEach(b=>{const cardsBox=el('div',{class:'bucket-cards'}),title=el('button',{type:'button',class:'bucket-title classify-destination','data-dest':b.bucketId,text:b.label}),bucket=el('section',{class:'bucket drop-target empty','data-drop-zone':b.bucketId},[title,cardsBox]);title.addEventListener('click',()=>activateDestination(b.bucketId));buckets.set(b.bucketId,bucket);grid.append(bucket)});
  shuffled(p.items).forEach(i=>{
    const card=el('button',{type:'button',class:'manip-card drag-card classify-card','data-card-id':i.itemId,'aria-pressed':'false'},[el('span',{class:'grip','aria-hidden':'true',text:'⠿'}),el('span',{class:'label',text:i.label})]);
    card.addEventListener('click',e=>{e.stopPropagation();if(card.dataset.suppressClick==='true'){card.dataset.suppressClick='false';return}selectCard(i.itemId)});
    pointerDrag(card,{
      onStart:()=>{clearDestinationSignals();card.classList.add('dragging');const r=card.getBoundingClientRect();card.style.width=`${r.width}px`},
      onMove:s=>{card.style.transform=`translate(${s.x-s.startX}px,${s.y-s.startY}px)`;stage.querySelectorAll('.eligible-zone').forEach(n=>n.classList.remove('eligible-zone'));const hit=targetAt(s.x,s.y,'[data-drop-zone]',card);markActive(hit?.querySelector('.classify-destination')||null);if(hit)hit.classList.add('eligible-zone')},
      onDrop:s=>{card.classList.remove('dragging');card.style.cssText='';markActive(null);clearDestinationSignals();const hit=targetAt(s.x,s.y,'[data-drop-zone]',card);if(s.moved&&hit)moveCard(i.itemId,hit.dataset.dropZone);if(s.moved){card.dataset.suppressClick='true';setTimeout(()=>card.dataset.suppressClick='false',0)}},
      onCancel:()=>{card.classList.remove('dragging');card.style.cssText='';markActive(null);clearDestinationSignals()}
    });
    cards.set(i.itemId,card);sourceCards.append(card)
  });
  paint();
  const send=primary('Émettre la réponse',()=>{if([...values.values()].some(x=>!x)){st.textContent='Classe toutes les cartes avant de continuer.';return}emit({assignments:p.items.map(i=>({itemId:i.itemId,bucketId:values.get(i.itemId)}))})});
  stage.append(header(v,'Candidate : sélectionner une carte révèle directement les buckets admissibles sans déplacer la mise en page.'),el('p',{text:p.prompt}),source,grid,st,el('div',{class:'actions'},[send]))
}


window.__LAB_RENDERERS__['classify-b']=classifyB;
})();
