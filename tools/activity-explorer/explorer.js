// No renderer implementation lives here. The exact production imports below are mandatory.
import { projectActivityPresentation } from '../../apps/learnit-next/src/integration/atlas/activity_projection.js';
import { renderActivityPresentation, readActivityResponse } from '../../apps/learnit-next/src/ui/activity_presenters.js';
import { evaluateActivityResponse } from '../../apps/learnit-next/src/core/activity_semantics.js';

const MAX_BYTES = 25 * 1024 * 1024;
const TYPES = Object.freeze({ lesson:'Leçon', flashcard:'Carte mémoire', qcm:'QCM', fill:'Texte à trous', matching:'Association', order:'Mise en ordre', classify:'Classement', constructed:'Réponse rédigée', productive:'Production' });
const PHASES = Object.freeze({ comprehension:'Compréhension', application:'Application', validation:'Validation', transfer:'Transfert', consolidation:'Consolidation', discovery:'Découverte', revision:'Révision' });
const ROLES = Object.freeze({ practice:'Entraînement', validation:'Validation', transfer:'Transfert', diagnostic:'Diagnostic' });
const $ = id => document.getElementById(id);
const ui = Object.freeze({
 file:$('kit-file'), search:$('activity-search'), course:$('course-filter'), type:$('activity-type'), list:$('activity-list'),
 kitTitle:$('kit-title'), kitCount:$('kit-count'), filterCount:$('filter-count'), status:$('explorer-status'),
 preview:$('activity-preview'), meta:$('activity-meta'), trail:$('activity-trail'), answer:$('answer-status'),
 attempt:$('try-answer'), reset:$('reset-preview'), progress:$('activity-progress'), tech:$('technical-info'), copy:$('copy-reference'),
 prev:[$('prev-top'),$('prev-bottom')],next:[$('next-top'),$('next-bottom')]
});
let epoch=0, kit=null, rows=[], visible=[], chosenId=null, active=null, presentation=null;
const activityName = row => row.activity.prompt || row.activity.title || row.activity.front || `Activité ${row.globalIndex + 1}`;
const text = (node,value) => { node.textContent=String(value ?? ''); };
function label(map,key){return map[key]||key||'Non renseigné';}
function disableActions(){ui.attempt.disabled=true;ui.reset.disabled=true;ui.prev.forEach(x=>x.disabled=true);ui.next.forEach(x=>x.disabled=true);ui.preview.replaceChildren();ui.meta.replaceChildren();ui.answer.textContent='';ui.trail.textContent='Aucune activité sélectionnée';ui.progress.textContent='—';ui.tech.replaceChildren();}
function setSelection(id){
 const row=visible.find(r=>r.id===id); if(!row){chosenId=null;active=null;presentation=null;disableActions();return;}
 chosenId=id;active=row.activity;ui.answer.textContent='';
 try{
   presentation=projectActivityPresentation(active,{assets:kit.assets??[],contract:kit.contract});
   const node=renderActivityPresentation(presentation);
   ui.preview.replaceChildren(node);
   // Do not infer media from activity fields: production projection resolves kit.assets references.
   const refs=active.media??[];
   if((presentation.media??[]).length!==refs.length)throw new Error('MEDIA_PROJECTION_INCOMPLETE');
   const at=visible.findIndex(r=>r.id===id);
   const span=(v,cls='chip')=>{const e=document.createElement('span');e.className=cls;e.textContent=v;return e;};
   ui.meta.replaceChildren(span(label(TYPES,active.type),'chip type'),span(label(PHASES,active.learningPhase),'chip'),...(active.assessmentRole?[span(label(ROLES,active.assessmentRole),'chip')]:[]));
   text(ui.trail,`${row.course.title} · Activité ${row.localIndex+1}`);
   text(ui.progress,`${at+1} sur ${visible.length}`);
   ui.prev.forEach(n=>n.disabled=at===0); ui.next.forEach(n=>n.disabled=at===visible.length-1);
   ui.attempt.disabled=['lesson','flashcard'].includes(active.type);ui.reset.disabled=false;
   ui.tech.replaceChildren(); const p=document.createElement('p');p.textContent=`Type : ${active.type} · Phase : ${active.learningPhase??'—'} · Révision : ${active.activityRevisionId??'—'} · Médias : ${(presentation.media??[]).length}`;ui.tech.append(p);
   ui.list.querySelectorAll('button[data-activity-id]').forEach(btn=>{const selected=btn.dataset.activityId===id;btn.classList.toggle('selected',selected);btn.setAttribute('aria-current',selected?'true':'false');if(selected)btn.scrollIntoView?.({block:'nearest'});});
 }catch(error){presentation=null;ui.preview.replaceChildren();disableActions();text(ui.status,`Aperçu refusé : ${error.message}`);}
}
function renderList(){
 const oldId=chosenId;
 const search=ui.search.value.normalize('NFC').toLocaleLowerCase('fr').trim(),course=ui.course.value,type=ui.type.value;
 visible=rows.filter(r=>(!course||r.course.courseLineageId===course)&&(!type||r.activity.type===type)&&(!search||`${r.course.title} ${label(TYPES,r.activity.type)} ${activityName(r)} ${r.activity.activityLineageId??''}`.normalize('NFC').toLocaleLowerCase('fr').includes(search)));
 ui.list.replaceChildren();text(ui.filterCount,`${visible.length} activité(s) sur ${rows.length}`);
 const fragment=document.createDocumentFragment();
 visible.forEach(row=>{
   const b=document.createElement('button');b.type='button';b.className='activity-row';b.dataset.activityId=row.id;
   const head=document.createElement('span');head.className='row-head';head.textContent=`${row.globalIndex+1}. ${label(TYPES,row.activity.type)}`;
   const name=document.createElement('span');name.className='row-name';name.textContent=activityName(row);
   const foot=document.createElement('span');foot.className='row-foot';foot.textContent=label(PHASES,row.activity.learningPhase);
   b.append(head,name,foot);b.addEventListener('click',()=>setSelection(row.id));fragment.append(b);
 });ui.list.append(fragment);
 setSelection(visible.some(r=>r.id===oldId)?oldId:visible[0]?.id);
}
function step(dir){const at=visible.findIndex(r=>r.id===chosenId);if(at>=0&&visible[at+dir])setSelection(visible[at+dir].id);}
async function openKit(file){
 const token=++epoch;kit=null;rows=[];visible=[];chosenId=null;active=null;presentation=null;disableActions();ui.list.replaceChildren();
 if(!file)return;
 if(file.size<=0||file.size>MAX_BYTES){text(ui.status,'Fichier refusé : vide ou supérieur à 25 Mio.');return;}
 text(ui.status,'Lecture et vérification du kit…');
 try{
   const parsed=JSON.parse(await file.text());if(token!==epoch)return;
   if(parsed.contract!=='learnit.kit.v6'||!Array.isArray(parsed.courses)||!parsed.courses.length)throw new Error('Le fichier doit être un kit LearnIT V6 avec au moins un cours.');
   if(parsed.assets!=null&&!Array.isArray(parsed.assets))throw new Error('Répertoire des médias invalide.');
   const assetIds=new Set();for(const a of parsed.assets??[]){if(!a||typeof a.assetId!=='string'||assetIds.has(a.assetId))throw new Error('Identité de média dupliquée ou invalide.');assetIds.add(a.assetId);}
   const next=[];const ids=new Set();let index=0;
   parsed.courses.forEach((course,ci)=>{if(!Array.isArray(course.activities))throw new Error(`Cours ${ci+1}: activities absent`);course.activities.forEach((activity,localIndex)=>{
     if(!activity||!TYPES[activity.type])throw new Error(`Activité ${index+1}: type inconnu`);
     const id=activity.activityLineageId;if(typeof id!=='string'||!id||ids.has(id))throw new Error(`Activité ${index+1}: identifiant dupliqué ou invalide`);ids.add(id);
     for(const ref of activity.media??[])if(!assetIds.has(ref.assetId))throw new Error(`Activité ${index+1}: image ${ref.assetId} introuvable dans le kit`);
     next.push({id,activity,course,globalIndex:index++,localIndex});
   })});
   if(!next.length)throw new Error('Aucune activité dans ce kit.');
   kit=parsed;rows=next;
   text(ui.kitTitle,parsed.title||file.name);text(ui.kitCount,`${parsed.courses.length} cours · ${rows.length} activités · ${(parsed.assets??[]).length} images`);
   ui.course.replaceChildren(new Option('Tous les cours',''));parsed.courses.forEach(c=>ui.course.append(new Option(c.title,c.courseLineageId)));
   ui.type.replaceChildren(new Option('Tous les types',''));[...new Set(rows.map(r=>r.activity.type))].sort().forEach(t=>ui.type.append(new Option(`${label(TYPES,t)} (${rows.filter(r=>r.activity.type===t).length})`,t)));
   ui.course.value='';ui.type.value='';ui.search.value='';
   text(ui.status,`Kit ouvert en lecture seule : ${rows.length} activités. Affichage canonique LearnIT activé. Contrôle Factory non exécuté.`);
   renderList();
 }catch(error){if(token===epoch)text(ui.status,`Ouverture refusée : ${error.message}`);}
}
ui.file.addEventListener('change',()=>{void openKit(ui.file.files?.[0])});
[ui.search,ui.course,ui.type].forEach(n=>n.addEventListener(n===ui.search?'input':'change',renderList));
ui.prev.forEach(n=>n.addEventListener('click',()=>step(-1)));ui.next.forEach(n=>n.addEventListener('click',()=>step(1)));
ui.reset.addEventListener('click',()=>chosenId&&setSelection(chosenId));
ui.attempt.addEventListener('click',()=>{
 if(!active||!presentation)return;
 try{const answer=readActivityResponse(ui.preview,presentation),score=evaluateActivityResponse(active,answer);
 text(ui.answer,score.scored?(score.correct?'Réponse correcte.':'Réponse incorrecte.'):'Réponse enregistrée pour cet essai, sans notation.');
 }catch(error){text(ui.answer,`Réponse incomplète ou invalide : ${error.message}`);}
});
ui.copy.addEventListener('click',()=>{if(!active)return;const info=`${kit.title}\n${active.activityLineageId}\n${active.activityRevisionId??''}`;if(navigator.clipboard?.writeText)void navigator.clipboard.writeText(info);else text(ui.status,'Copie indisponible dans ce navigateur.');});
document.addEventListener('keydown',event=>{if(event.key!=='ArrowLeft'&&event.key!=='ArrowRight')return;
 const el=event.target;if(el?.closest?.('input,textarea,select,[contenteditable="true"],.activity-presentation'))return;
 event.preventDefault();step(event.key==='ArrowRight'?1:-1);
});
text(ui.status,'Moteur LearnIT chargé. Sélectionnez un kit JSON pour explorer ses activités.');
document.documentElement.dataset.explorerReady='true';
