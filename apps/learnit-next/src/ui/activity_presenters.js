import { renderEmbeddedMediaSet } from './media.js';

let sequence = 0;
let randomSource = () => Math.random();
const uid = prefix => prefix + '-' + (++sequence);

export function setActivityPresenterRandomSourceForTest(source = null) {
  if (source != null && typeof source !== 'function') throw new TypeError('Random source must be a function or null');
  randomSource = source ?? (() => Math.random());
}
function shuffledOnce(values = []) {
  const out = [...values];
  for (let i = out.length - 1; i > 0; i -= 1) {
    const draw = Number(randomSource());
    const bounded = Number.isFinite(draw) ? Math.max(0, Math.min(.999999999999, draw)) : 0;
    const j = Math.floor(bounded * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}
function el(tag, attrs = {}, children = []) {
  const out = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value == null) continue;
    if (name === 'className') out.className = value;
    else if (name === 'text') out.textContent = String(value);
    else if (name === 'disabled') out.disabled = Boolean(value);
    else if (name === 'value') out.value = String(value);
    else out.setAttribute(name, String(value));
  }
  for (const child of (Array.isArray(children) ? children : [children])) {
    if (child == null) continue;
    out.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return out;
}
function required(message) { const error = new Error(message); error.code = 'ACTIVITY_RESPONSE_REQUIRED'; return error; }
const prompt = text => el('p', { className: 'atlas-question activity-prompt' }, [el('strong', { text })]);

function referenceDisclosure(references = []) {
  if (!references.length) return null;
  const list = el('ul', { className: 'activity-reference-list' });
  references.forEach(reference => {
    const external = 'Lien externe — s’ouvre dans un nouvel onglet';
    const link = el('a', {
      href: reference.url, target: '_blank', rel: 'noopener noreferrer',
      className: 'activity-reference-link', 'data-activity-reference-external': 'true',
      'aria-label': reference.label + '. ' + external,
    }, [
      el('span', { text: reference.label }),
      el('span', { className: 'activity-reference-external-mark', 'aria-hidden': 'true', text: '↗' }),
      el('span', { className: 'sr-only visually-hidden', text: '. ' + external }),
    ]);
    list.append(el('li', {}, [link, el('p', { className: 'activity-reference-hook', text: reference.hook })]));
  });
  return el('details', { className: 'activity-references', 'data-activity-references': 'closed' }, [
    el('summary', { text: 'Pour aller plus loin' }),
    el('div', { className: 'activity-references-body' }, [el('h3', { text: 'Références' }), list]),
  ]);
}
function mediaBlock(presentation, placement) {
  const items = (presentation.media ?? []).filter(item => String(item?.placement ?? 'content') === placement);
  if (!items.length) return null;
  return el('div', {
    className: 'activity-media-placement activity-media-placement-' + placement,
    'data-activity-media-placement-group': placement,
  }, [renderEmbeddedMediaSet(items)]);
}
function shell(presentation, children) {
  const root = el('section', {
    className: 'activity-presentation activity-presentation-' + presentation.type,
    'data-activity-presentation': presentation.type,
  }, children);
  const promptMedia = mediaBlock(presentation, 'prompt');
  if (promptMedia) {
    const anchor = root.querySelector('.activity-prompt');
    if (anchor) anchor.after(promptMedia); else root.prepend(promptMedia);
  }
  const contentMedia = mediaBlock(presentation, 'content');
  if (contentMedia) root.append(contentMedia);
  const references = referenceDisclosure(presentation.references ?? []);
  if (references) root.append(references);
  return root;
}
function keyActivate(node, fn) {
  node.addEventListener('keydown', event => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault(); fn(event);
  });
}
function pointerDrag(node, handlers = {}) {
  let state = null;
  node.addEventListener('pointerdown', event => {
    if (event.button != null && event.button !== 0) return;
    state = { pointerId:event.pointerId, startX:event.clientX, startY:event.clientY, x:event.clientX, y:event.clientY, moved:false };
    node.setPointerCapture?.(event.pointerId); handlers.onStart?.(state, event);
  });
  node.addEventListener('pointermove', event => {
    if (!state || event.pointerId !== state.pointerId) return;
    state.x = event.clientX; state.y = event.clientY;
    if (!state.moved && Math.hypot(state.x-state.startX, state.y-state.startY) >= 5) state.moved = true;
    handlers.onMove?.(state, event);
  });
  const finish = (kind, event) => {
    if (!state || event.pointerId !== state.pointerId) return;
    const done = state; state = null;
    try { handlers[kind]?.(done, event); } finally { node.releasePointerCapture?.(event.pointerId); }
  };
  node.addEventListener('pointerup', event => finish('onDrop', event));
  node.addEventListener('pointercancel', event => finish('onCancel', event));
}
function targetAt(x, y, selector, dragged = null) {
  for (const candidate of document.elementsFromPoint(x, y)) {
    const target = candidate.closest?.(selector);
    if (target && (!dragged || !target.contains(dragged))) return target;
  }
  return null;
}
function clearSignals(root) {
  root.querySelectorAll('.eligible-destination,.active-destination,.eligible-zone')
    .forEach(node => node.classList.remove('eligible-destination','active-destination','eligible-zone'));
}
function markActive(root, target) {
  root.querySelectorAll('.active-destination').forEach(node => node.classList.remove('active-destination'));
  if (target) target.classList.add('active-destination');
}
function setPressed(map, id) { map.forEach((node,key) => node.setAttribute('aria-pressed', String(key === id))); }

function qcm(p) {
  const fieldset = el('fieldset', { className:'answer-fieldset activity-qcm-options' }, [el('legend',{text:'Choisissez une réponse'})]);
  const name = uid('activity-qcm');
  shuffledOnce(p.choices).forEach((choice,index) => {
    const id = uid('activity-qcm-choice-' + index);
    fieldset.append(el('label',{className:'choice-row activity-qcm-option',for:id},[
      el('input',{id,type:'radio',name,value:choice.choiceId,'data-activity-choice':'true'}),
      el('span',{className:'activity-qcm-label',text:choice.label}),
    ]));
  });
  return shell(p,[prompt(p.prompt),fieldset]);
}
function lesson(p) {
  const body=el('div',{className:'activity-lesson-body'});
  String(p.body||'').split(/\n\s*\n/).map(x=>x.trim()).filter(Boolean).forEach(x=>body.append(el('p',{text:x})));
  const card=el('div',{className:'activity-learning-card'},[el('p',{className:'activity-kind',text:'À retenir'}),el('h2',{text:p.title}),body]);
  if(p.keyPoints?.length) card.append(el('section',{className:'activity-key-points','aria-label':'Points clés'},[el('h3',{text:'Points clés'}),el('ul',{},p.keyPoints.map(x=>el('li',{text:x})))]));
  if(p.contextNote?.trim()) card.append(el('aside',{className:'activity-context-note','aria-label':'Contexte'},[el('strong',{text:'Contexte'}),el('p',{text:p.contextNote.trim()})]));
  const button=el('button',{type:'button',className:'atlas-primary activity-continue',text:'Continuer','data-activity-continue':'lesson'});
  const root=shell(p,[card,el('div',{className:'activity-local-actions'},[button])]);
  button.addEventListener('click',()=>{root.dataset.activityReady='true';button.disabled=true;button.textContent='Prêt à continuer';});
  return root;
}
function flashcard(p) {
  let revealed=false;
  const status=el('p',{className:'activity-interaction-status',role:'status','aria-live':'polite',text:'Activez la carte pour voir la réponse.'});
  const front=el('div',{className:'activity-flash-face activity-flash-front'},[el('div',{className:'activity-flash-section'},[el('span',{className:'activity-small-label',text:'Question'}),el('h3',{text:p.front})])]);
  const back=el('div',{className:'activity-flash-face activity-flash-back'},[
    el('div',{className:'activity-flash-section activity-flash-question-repeat'},[el('span',{className:'activity-small-label',text:'Question'}),el('strong',{text:p.front})]),
    el('div',{className:'activity-flash-section activity-flash-answer'},[el('span',{className:'activity-small-label',text:'Réponse'}),el('strong',{text:p.back})]),
    el('p',{className:'activity-flash-explanation',text:p.explanation}),
  ]);
  const card=el('button',{type:'button',className:'activity-flash-card','aria-label':'Retourner la carte','aria-pressed':'false'},[el('div',{className:'activity-flash-inner'},[front,back])]);
  const next=el('button',{type:'button',className:'atlas-primary',text:'Continuer','data-activity-continue':'flashcard'}); next.hidden=true;
  const root=shell(p,[el('section',{className:'activity-flash-shell'},[card,status,el('div',{className:'activity-local-actions'},[next])])]);
  card.addEventListener('click',()=>{const toBack=!card.classList.contains('is-back');card.classList.toggle('is-back',toBack);card.setAttribute('aria-pressed',String(toBack));if(toBack){revealed=true;root.dataset.flashcardRevealed='true';next.hidden=false;status.textContent='Réponse affichée. La question reste rappelée en haut.';}else status.textContent='Question affichée.';});
  next.addEventListener('click',()=>{if(!revealed)return;root.dataset.activityReady='true';next.disabled=true;next.textContent='Prêt à continuer';});
  return root;
}
function associations(root) {
  return new Map([...root.querySelectorAll('[data-matching-association="true"]')].map(node=>[node.dataset.leftItemId,node.dataset.rightItemId]));
}
function matching(p) {
  const map=new Map(),cards=new Map(),rows=new Map(); let selected=null;
  const status=el('p',{className:'activity-interaction-status',role:'status','aria-live':'polite',text:'Glissez une carte vers une description, ou sélectionnez-la puis choisissez une destination.'});
  const sourceHead=el('div',{className:'activity-match-source-head'},[el('h3',{text:'Cartes à placer'}),el('span',{className:'help activity-match-count'})]);
  const source=el('div',{className:'activity-match-source'}), sourceWrap=el('section',{className:'activity-match-source-wrap'},[sourceHead,source]), board=el('section',{className:'activity-pair-board'});
  const root=shell(p,[prompt(p.prompt),sourceWrap,board,status]);
  const paint=()=>{sourceHead.querySelector('.activity-match-count').textContent=source.querySelectorAll(':scope > .activity-match-card').length+' restante(s)';for(const [id,row] of rows){const filled=[...map.values()].includes(id);row.classList.toggle('matched',filled);row.querySelector('.activity-pair-slot').classList.toggle('filled',filled);}status.textContent=map.size+'/'+p.leftItems.length+' association(s).';};
  const clear=()=>{selected=null;setPressed(cards,null);clearSignals(root);};
  const select=id=>{selected=id;setPressed(cards,id);clearSignals(root);const current=map.get(id);[...board.querySelectorAll('.activity-pair-target')].filter(t=>t.dataset.targetId!==current).forEach(t=>t.classList.add('eligible-destination'));status.textContent='Carte sélectionnée. Les destinations possibles sont indiquées.';};
  const unlink=card=>{card.removeAttribute('data-matching-association');card.removeAttribute('data-left-item-id');card.removeAttribute('data-right-item-id');};
  const place=(leftId,rightId)=>{const slot=rows.get(rightId).querySelector('.activity-pair-slot'), incoming=cards.get(leftId), occupant=slot.querySelector('.activity-match-card');if(occupant&&occupant!==incoming){map.delete(occupant.dataset.cardId);unlink(occupant);source.append(occupant);}for(const [l,r] of [...map])if(l===leftId||r===rightId)map.delete(l);map.set(leftId,rightId);incoming.setAttribute('data-matching-association','true');incoming.dataset.leftItemId=leftId;incoming.dataset.rightItemId=rightId;slot.append(incoming);clear();paint();};
  shuffledOnce(p.rightItems).forEach(right=>{const slot=el('div',{className:'activity-pair-slot','data-target-id':right.itemId}),target=el('button',{type:'button',className:'activity-pair-target activity-manip-card','data-target-id':right.itemId,text:right.label}),row=el('div',{className:'activity-pair-row','data-target-id':right.itemId},[slot,el('span',{className:'activity-pair-connector','aria-hidden':'true',text:'↔'}),target]);target.addEventListener('click',()=>selected&&place(selected,right.itemId));rows.set(right.itemId,row);board.append(row);});
  shuffledOnce(p.leftItems).forEach(item=>{const card=el('button',{type:'button',className:'activity-manip-card activity-drag-card activity-match-card','data-card-id':item.itemId,'aria-pressed':'false'},[el('span',{className:'activity-grip','aria-hidden':'true',text:'⠿'}),el('span',{text:item.label})]);card.addEventListener('click',event=>{event.stopPropagation();if(card.dataset.suppressClick==='true'){card.dataset.suppressClick='false';return;}select(item.itemId);});pointerDrag(card,{onStart:()=>{clearSignals(root);card.classList.add('dragging');card.style.width=card.getBoundingClientRect().width+'px';},onMove:s=>{if(!s.moved)return;card.style.transform='translate('+(s.x-s.startX)+'px,'+(s.y-s.startY)+'px)';const hit=targetAt(s.x,s.y,'.activity-pair-row',card);markActive(root,hit?.querySelector('.activity-pair-target')??null);},onDrop:s=>{const hit=targetAt(s.x,s.y,'.activity-pair-row',card);card.classList.remove('dragging');card.style.cssText='';markActive(root,null);if(s.moved&&hit)place(item.itemId,hit.dataset.targetId);else clearSignals(root);if(s.moved){card.dataset.suppressClick='true';setTimeout(()=>{card.dataset.suppressClick='false';},0);}},onCancel:()=>{card.classList.remove('dragging');card.style.cssText='';markActive(root,null);clearSignals(root);}});cards.set(item.itemId,card);source.append(card);});
  paint(); return root;
}
function order(p) {
  const status=el('p',{className:'activity-interaction-status',role:'status','aria-live':'polite',text:'Glissez verticalement une étiquette, ou sélectionnez-la puis choisissez un intercalaire.'});
  const list=el('div',{className:'activity-order-b-list',role:'list','data-order-list':'true'}), overlay=el('div',{className:'activity-order-insert-overlay','aria-hidden':'true'}); list.append(overlay);
  let selected=null; const cards=new Map(); const cardNodes=()=>[...list.querySelectorAll(':scope > .activity-order-b-card')];
  const clearOverlay=()=>{overlay.replaceChildren();overlay.classList.remove('visible');overlay.setAttribute('aria-hidden','true');list.classList.remove('placing');};
  const clear=()=>{selected=null;setPressed(cards,null);clearOverlay();};
  const restore=(row,s)=>{if(s.originalStyle==null)row.removeAttribute('style');else row.setAttribute('style',s.originalStyle);row.classList.remove('drag-source');};
  const moveBefore=beforeId=>{if(!selected)return;const row=cards.get(selected),before=beforeId?cards.get(beforeId):null;if(before===row){clear();return;}if(before)list.insertBefore(row,before);else list.insertBefore(row,overlay);clear();status.textContent='Ordre mis à jour.';};
  const makeSlot=(top,beforeId,label)=>{const slot=el('button',{type:'button',className:'activity-order-insert-slot eligible-destination','data-before-id':beforeId??'','aria-label':label},[el('span',{className:'activity-order-insert-line','aria-hidden':'true'})]);slot.style.top=top+'px';slot.addEventListener('click',()=>moveBefore(beforeId));overlay.append(slot);};
  const showOverlay=()=>{clearOverlay();if(!selected)return;const nodes=cardNodes();if(!nodes.length)return;const lr=list.getBoundingClientRect(),rs=nodes.map(n=>n.getBoundingClientRect());makeSlot(rs[0].top-lr.top,nodes[0].dataset.orderItem,'Placer avant '+nodes[0].querySelector('.activity-order-b-label').textContent);for(let i=1;i<nodes.length;i+=1)makeSlot(((rs[i-1].bottom+rs[i].top)/2)-lr.top,nodes[i].dataset.orderItem,'Placer avant '+nodes[i].querySelector('.activity-order-b-label').textContent);makeSlot(rs.at(-1).bottom-lr.top,null,'Placer à la fin');overlay.classList.add('visible');overlay.setAttribute('aria-hidden','false');list.classList.add('placing');};
  const select=row=>{selected=row.dataset.orderItem;setPressed(cards,selected);showOverlay();status.textContent='Étiquette sélectionnée. Les intercalaires indiquent les positions possibles.';};
  shuffledOnce(p.items).forEach(item=>{const row=el('div',{className:'activity-manip-card activity-order-b-card activity-drag-card',role:'button',tabindex:'0','data-order-item':item.itemId,'aria-pressed':'false','aria-label':item.label+'. Activer pour choisir une position.'},[el('span',{className:'activity-grip','aria-hidden':'true',text:'⠿'}),el('span',{className:'activity-order-b-label',text:item.label})]);row.addEventListener('click',()=>{if(row.dataset.suppressClick==='true'){row.dataset.suppressClick='false';return;}select(row);});keyActivate(row,()=>select(row));pointerDrag(row,{onStart:(s,e)=>{const r=row.getBoundingClientRect(),lr=list.getBoundingClientRect();s.offsetY=e.clientY-r.top;s.fixedLeft=r.left;s.width=r.width;s.height=r.height;s.sourceRect={x:r.x,y:r.y};s.listRect={x:lr.x,y:lr.y};s.originalStyle=row.getAttribute('style');s.active=false;},onMove:s=>{if(!s.moved)return;if(!s.active){s.active=true;clear();const ph=el('div',{className:'activity-order-placeholder active-destination','aria-hidden':'true','data-source-id':item.itemId});ph.style.boxSizing='border-box';ph.style.width=s.width+'px';ph.style.height=s.height+'px';ph.style.minHeight=s.height+'px';ph.style.maxHeight=s.height+'px';ph.style.padding='0';ph.style.margin='0';s.placeholder=ph;row.classList.add('drag-source');row.style.position='absolute';row.style.left=(s.sourceRect.x-s.listRect.x)+'px';row.style.top=(s.sourceRect.y-s.listRect.y)+'px';row.style.width=s.width+'px';row.style.height=s.height+'px';row.style.minHeight=s.height+'px';row.style.maxHeight=s.height+'px';row.style.margin='0';row.style.opacity='0';row.style.zIndex='-1';list.insertBefore(ph,row);const ghost=row.cloneNode(true);ghost.classList.remove('activity-drag-card','drag-source');ghost.classList.add('activity-order-ghost','dragging');ghost.removeAttribute('tabindex');ghost.setAttribute('aria-hidden','true');ghost.style.position='fixed';ghost.style.opacity='.98';ghost.style.zIndex='9999';ghost.style.left=s.fixedLeft+'px';ghost.style.top=(s.startY-s.offsetY)+'px';ghost.style.width=s.width+'px';ghost.style.height=s.height+'px';ghost.style.minHeight=s.height+'px';ghost.style.maxHeight=s.height+'px';document.body.append(ghost);s.ghost=ghost;status.textContent='Déplacement vertical en cours.';}s.ghost.style.left=s.fixedLeft+'px';s.ghost.style.top=(s.y-s.offsetY)+'px';const others=cardNodes().filter(x=>x!==row);let placed=false;for(const other of others){const r=other.getBoundingClientRect();if(s.y<r.top+r.height/2){list.insertBefore(s.placeholder,other);placed=true;break;}}if(!placed)list.insertBefore(s.placeholder,overlay);},onDrop:s=>{if(!s.active)return;s.ghost?.remove();if(s.placeholder){list.insertBefore(row,s.placeholder);s.placeholder.remove();}restore(row,s);row.dataset.suppressClick='true';setTimeout(()=>{row.dataset.suppressClick='false';},0);status.textContent='Ordre mis à jour.';},onCancel:s=>{if(!s.active)return;s.ghost?.remove();s.placeholder?.remove();restore(row,s);status.textContent='Déplacement annulé.';}});cards.set(item.itemId,row);list.insertBefore(row,overlay);});
  return shell(p,[prompt(p.prompt),el('p',{className:'help',text:'La poignée ⠿ est seulement un indice visuel : toute l’étiquette peut être saisie.'}),list,status]);
}
function classify(p) {
  const cards=new Map(),buckets=new Map();let selected=null;
  const status=el('p',{className:'activity-interaction-status',role:'status','aria-live':'polite',text:'Glissez une carte ou sélectionnez-la puis choisissez une catégorie.'}),sourceTitle=el('button',{type:'button',className:'activity-bucket-title activity-classify-destination','data-dest':'source',text:'À classer'}),sourceCards=el('div',{className:'activity-classify-source-cards'}),source=el('section',{className:'activity-classify-source activity-drop-target','data-drop-zone':'source'},[sourceTitle,sourceCards]),grid=el('section',{className:'activity-bucket-grid'});
  const root=shell(p,[prompt(p.prompt),source,grid,status]), current=id=>cards.get(id)?.dataset.classifyBucket||'source';
  const clear=()=>{selected=null;setPressed(cards,null);clearSignals(root);};
  const show=id=>{clearSignals(root);const now=current(id);if(now!=='source'){sourceTitle.classList.add('eligible-destination');source.classList.add('eligible-zone');}for(const [bid,b] of buckets)if(bid!==now){b.querySelector('.activity-classify-destination').classList.add('eligible-destination');b.classList.add('eligible-zone');}};
  const paint=()=>{for(const b of buckets.values())b.classList.toggle('empty',b.querySelector('.activity-bucket-cards').children.length===0);source.classList.toggle('empty',sourceCards.children.length===0);status.textContent=[...cards.values()].filter(c=>c.dataset.classifyBucket).length+'/'+p.items.length+' carte(s) classée(s).';};
  const select=id=>{selected=id;setPressed(cards,id);show(id);status.textContent='Carte sélectionnée. Les catégories possibles sont indiquées.';};
  const move=(id,dest)=>{const card=cards.get(id);if(dest==='source'){card.dataset.classifyBucket='';sourceCards.append(card);}else{card.dataset.classifyBucket=dest;buckets.get(dest).querySelector('.activity-bucket-cards').append(card);}clear();paint();};
  const activate=dest=>{if(selected&&dest!==current(selected))move(selected,dest);};sourceTitle.addEventListener('click',()=>activate('source'));
  p.buckets.forEach(bucket=>{const box=el('div',{className:'activity-bucket-cards'}),title=el('button',{type:'button',className:'activity-bucket-title activity-classify-destination','data-dest':bucket.bucketId,text:bucket.label}),node=el('section',{className:'activity-bucket activity-drop-target empty','data-drop-zone':bucket.bucketId},[title,box]);title.addEventListener('click',()=>activate(bucket.bucketId));buckets.set(bucket.bucketId,node);grid.append(node);});
  shuffledOnce(p.items).forEach(item=>{const card=el('button',{type:'button',className:'activity-manip-card activity-drag-card activity-classify-card','data-classify-item':item.itemId,'data-classify-bucket':'','aria-pressed':'false'},[el('span',{className:'activity-grip','aria-hidden':'true',text:'⠿'}),el('span',{className:'activity-classify-label',text:item.label})]);card.addEventListener('click',e=>{e.stopPropagation();if(card.dataset.suppressClick==='true'){card.dataset.suppressClick='false';return;}select(item.itemId);});pointerDrag(card,{onStart:()=>{clearSignals(root);card.classList.add('dragging');card.style.width=card.getBoundingClientRect().width+'px';},onMove:s=>{if(!s.moved)return;card.style.transform='translate('+(s.x-s.startX)+'px,'+(s.y-s.startY)+'px)';root.querySelectorAll('.eligible-zone').forEach(n=>n.classList.remove('eligible-zone'));const hit=targetAt(s.x,s.y,'[data-drop-zone]',card);markActive(root,hit?.querySelector('.activity-classify-destination')??null);if(hit)hit.classList.add('eligible-zone');},onDrop:s=>{const hit=targetAt(s.x,s.y,'[data-drop-zone]',card);card.classList.remove('dragging');card.style.cssText='';markActive(root,null);clearSignals(root);if(s.moved&&hit)move(item.itemId,hit.dataset.dropZone);if(s.moved){card.dataset.suppressClick='true';setTimeout(()=>{card.dataset.suppressClick='false';},0);}},onCancel:()=>{card.classList.remove('dragging');card.style.cssText='';markActive(root,null);clearSignals(root);}});cards.set(item.itemId,card);sourceCards.append(card);});paint();return root;
}
function fill(p) {
  const assignments=new Map(),tokens=new Map(),slots=new Map();let selected=null;
  const status=el('p',{className:'activity-interaction-status',role:'status','aria-live':'polite',text:'Glissez un mot ou sélectionnez-le puis choisissez un emplacement.'}),bankTitle=el('button',{type:'button',className:'activity-fill-bank-title',text:'Mots disponibles','aria-label':'Mots disponibles — remettre le mot sélectionné dans la banque'}),bankBox=el('div',{className:'activity-token-bank'}),bank=el('section',{className:'activity-fill-bank activity-drop-target','data-fill-drop':'bank'},[bankTitle,bankBox]),sentence=el('div',{className:'activity-fill-b-sentence'});
  const root=shell(p,[prompt(p.prompt),bank,sentence,status]), location=id=>{for(const [slot,token] of assignments)if(token===id)return slot;return'bank';};
  const clear=()=>{selected=null;setPressed(tokens,null);clearSignals(root);};
  const paint=()=>{for(const [id,slot] of slots){const filled=assignments.has(id);slot.classList.toggle('filled',filled);slot.classList.toggle('empty',!filled);if(filled){slot.removeAttribute('role');slot.removeAttribute('tabindex');}else{slot.setAttribute('role','button');slot.setAttribute('tabindex','0');}slot.dataset.tokenId=assignments.get(id)??'';}status.textContent=assignments.size+'/'+slots.size+' emplacement(s) rempli(s).';};
  const show=id=>{clearSignals(root);for(const [sid,slot] of slots)if(!assignments.has(sid))slot.classList.add('eligible-destination');if(location(id)!=='bank')bankTitle.classList.add('eligible-destination');};
  const select=id=>{selected=id;setPressed(tokens,id);show(id);status.textContent='Mot sélectionné. Les emplacements possibles sont indiqués.';};
  const put=(tokenId,slotId)=>{const token=tokens.get(tokenId);for(const [s,t] of [...assignments])if(t===tokenId)assignments.delete(s);const old=assignments.get(slotId);if(old&&old!==tokenId)bankBox.append(tokens.get(old));assignments.set(slotId,tokenId);slots.get(slotId).append(token);clear();paint();};
  const returnBank=id=>{for(const [s,t] of [...assignments])if(t===id)assignments.delete(s);bankBox.append(tokens.get(id));clear();paint();};bankTitle.addEventListener('click',()=>selected&&returnBank(selected));
  p.segments.forEach(segment=>{if(Object.hasOwn(segment,'text'))sentence.append(el('span',{text:segment.text}));else{const slot=el('span',{className:'activity-fill-b-slot empty activity-drop-target','data-fill-drop':segment.slotId,'data-activity-slot':segment.slotId,'data-token-id':'',role:'button',tabindex:'0','aria-label':'Emplacement '+segment.slotId});slot.addEventListener('click',e=>{if(e.target.closest('.activity-token-chip'))return;if(selected&&!assignments.has(segment.slotId))put(selected,segment.slotId);});keyActivate(slot,()=>selected&&!assignments.has(segment.slotId)&&put(selected,segment.slotId));slots.set(segment.slotId,slot);sentence.append(slot);}});
  shuffledOnce(p.tokens).forEach(token=>{const chip=el('button',{type:'button',className:'activity-manip-card activity-drag-card activity-token-chip','data-token-id':token.tokenId,'aria-pressed':'false'},[el('span',{className:'activity-grip','aria-hidden':'true',text:'⠿'}),el('span',{text:token.label})]);chip.addEventListener('click',e=>{e.stopPropagation();if(chip.dataset.suppressClick==='true'){chip.dataset.suppressClick='false';return;}select(token.tokenId);});pointerDrag(chip,{onStart:()=>{clearSignals(root);chip.classList.add('dragging');chip.style.width=chip.getBoundingClientRect().width+'px';},onMove:s=>{if(!s.moved)return;chip.style.transform='translate('+(s.x-s.startX)+'px,'+(s.y-s.startY)+'px)';const hit=targetAt(s.x,s.y,'[data-fill-drop]',chip);markActive(root,hit?.matches('.activity-fill-b-slot')?hit:hit?.querySelector('.activity-fill-bank-title')??null);},onDrop:s=>{const hit=targetAt(s.x,s.y,'[data-fill-drop]',chip);chip.classList.remove('dragging');chip.style.cssText='';markActive(root,null);clearSignals(root);if(s.moved&&hit){const dest=hit.dataset.fillDrop;if(dest==='bank')returnBank(token.tokenId);else put(token.tokenId,dest);}if(s.moved){chip.dataset.suppressClick='true';setTimeout(()=>{chip.dataset.suppressClick='false';},0);}},onCancel:()=>{chip.classList.remove('dragging');chip.style.cssText='';markActive(root,null);clearSignals(root);}});tokens.set(token.tokenId,chip);bankBox.append(chip);});paint();return root;
}
function constructed(p) {
  const id=uid('activity-constructed');
  return shell(p,[prompt(p.prompt),el('div',{className:'activity-constructed'},[el('label',{for:id,text:'Votre réponse'}),el('textarea',{id,rows:'6',maxlength:'4000','data-constructed-response':'true'}),el('p',{className:'help',text:'Réponse attendue : un texte non vide.'})])]);
}

export function renderActivityPresentation(presentation) {
  if (!presentation || typeof presentation !== 'object') throw new TypeError('ActivityPresentation object is required');
  switch (presentation.type) {
    case 'qcm': return qcm(presentation);
    case 'fill': return fill(presentation);
    case 'lesson': return lesson(presentation);
    case 'flashcard': return flashcard(presentation);
    case 'matching': return matching(presentation);
    case 'order': return order(presentation);
    case 'classify': return classify(presentation);
    case 'constructed': return constructed(presentation);
    default: throw new Error('ACTIVITY_PRESENTATION_TYPE_UNSUPPORTED: ' + presentation.type);
  }
}
export function readActivityResponse(container, presentation) {
  if (!(container instanceof Element) || !presentation || typeof presentation !== 'object') throw new TypeError('Activity response container and presentation are required');
  if (presentation.type === 'qcm') {
    const selected=container.querySelector('[data-activity-choice="true"]:checked');
    if(!selected)throw required('Choisissez une réponse avant de continuer.');
    return { choiceId:selected.value };
  }
  if (presentation.type === 'fill') {
    const answer={};
    for(const slot of container.querySelectorAll('[data-activity-slot]')) {
      const value=slot.matches('select')?slot.value:slot.dataset.tokenId;
      if(!value)throw required('Complétez toutes les réponses avant de continuer.');
      answer[slot.dataset.activitySlot]=value;
    }
    return answer;
  }
  const root=container.querySelector('[data-activity-presentation="'+presentation.type+'"]');
  if(presentation.type==='lesson'){if(root?.dataset.activityReady!=='true')throw required('Utilisez Continuer après avoir lu la leçon.');return {acknowledged:true};}
  if(presentation.type==='flashcard'){if(root?.dataset.flashcardRevealed!=='true'||root.dataset.activityReady!=='true')throw required('Affichez la réponse puis utilisez Continuer.');return {revealed:true};}
  if(presentation.type==='matching'){const map=associations(root);if(map.size!==presentation.leftItems.length)throw required('Associez chaque élément de gauche avant de continuer.');return {associations:presentation.leftItems.map(item=>({leftItemId:item.itemId,rightItemId:map.get(item.itemId)}))};}
  if(presentation.type==='order'){const orderedItemIds=[...root.querySelectorAll('[data-order-item]')].map(item=>item.dataset.orderItem);if(orderedItemIds.length!==presentation.items.length)throw required('Ordre incomplet.');return {orderedItemIds};}
  if(presentation.type==='classify'){const assignments=[...root.querySelectorAll('[data-classify-item]')].map(card=>({itemId:card.dataset.classifyItem,bucketId:card.dataset.classifyBucket})).filter(item=>item.bucketId);if(assignments.length!==presentation.items.length)throw required('Classez chaque élément avant de continuer.');return {assignments:presentation.items.map(item=>assignments.find(candidate=>candidate.itemId===item.itemId))};}
  if(presentation.type==='constructed'){const text=root.querySelector('[data-constructed-response]')?.value?.trim()||'';if(!text)throw required('Saisissez une réponse avant de continuer.');return {text};}
  throw new Error('ACTIVITY_PRESENTATION_TYPE_UNSUPPORTED: '+presentation.type);
}
