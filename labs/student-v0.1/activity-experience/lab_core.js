(()=>{
'use strict';
const fixtures=JSON.parse(document.querySelector('#fixtures').textContent);
const variants=JSON.parse(document.querySelector('#variants').textContent);
const select=document.querySelector('#variant');
const stage=document.querySelector('#stage');
const response=document.querySelector('#response');
const note=document.querySelector('#variant-note');
let attemptSeed=1, rng=()=>0.5;
const el=(tag,attrs={},children=[])=>{const n=document.createElement(tag);for(const[k,v]of Object.entries(attrs)){if(v==null)continue;if(k==='text')n.textContent=String(v);else if(k==='class')n.className=v;else if(k==='checked')n.checked=!!v;else n.setAttribute(k,String(v))}for(const c of [].concat(children))if(c!=null)n.append(c?.nodeType?c:document.createTextNode(String(c)));return n};
const emit=value=>{response.textContent=JSON.stringify(value,null,2);response.dataset.emitted='true'};
const reset=()=>{response.textContent='Aucune réponse émise.';delete response.dataset.emitted;stage.replaceChildren()};
const header=(v,description)=>el('div',{class:'variant-header'},[el('p',{class:'eyebrow',text:v.id}),el('h2',{text:v.label}),el('p',{class:'variant-description',text:description})]);
const status=(text='')=>el('p',{class:'status',role:'status','aria-live':'polite',text});
const primary=(label,fn)=>{const b=el('button',{type:'button',class:'primary',text:label});b.addEventListener('click',fn);return b};
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function newSeed(){if(Array.isArray(window.__LAB_TEST_SEEDS__)&&window.__LAB_TEST_SEEDS__.length)return Number(window.__LAB_TEST_SEEDS__.shift())>>>0;try{const a=new Uint32Array(1);crypto.getRandomValues(a);if(a[0])return a[0]>>>0}catch{}return(Math.random()*0xffffffff)>>>0||1}
function beginAttempt(){attemptSeed=newSeed();rng=mulberry32(attemptSeed);return attemptSeed}
function shuffled(items){const a=[...items];for(let i=a.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
function pointerDrag(node,{onStart,onMove,onDrop,onCancel}){let drag=null;const end=(e,cancel)=>{if(!drag||e.pointerId!==drag.pointerId)return;try{node.releasePointerCapture?.(e.pointerId)}catch{}const d=drag;drag=null;(cancel?onCancel:onDrop)?.(d,e)};node.addEventListener('pointerdown',e=>{if(drag||e.button!==0)return;drag={pointerId:e.pointerId,startX:e.clientX,startY:e.clientY,x:e.clientX,y:e.clientY,moved:false};node.setPointerCapture?.(e.pointerId);onStart?.(drag,e)});node.addEventListener('pointermove',e=>{if(!drag||e.pointerId!==drag.pointerId)return;drag.x=e.clientX;drag.y=e.clientY;if(Math.abs(drag.x-drag.startX)+Math.abs(drag.y-drag.startY)>5)drag.moved=true;onMove?.(drag,e)});node.addEventListener('pointerup',e=>end(e,false));node.addEventListener('pointercancel',e=>end(e,true))}
window.__LAB_CORE__={fixtures,variants,select,stage,response,note,el,emit,reset,header,status,primary,pointerDrag,beginAttempt,shuffled,get attemptSeed(){return attemptSeed}};
window.__LAB_RENDERERS__={};
})();
