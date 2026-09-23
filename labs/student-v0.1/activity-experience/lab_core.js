(()=>{
'use strict';
const fixtures=JSON.parse(document.querySelector('#fixtures').textContent);
const variants=JSON.parse(document.querySelector('#variants').textContent);
const select=document.querySelector('#variant');
const stage=document.querySelector('#stage');
const response=document.querySelector('#response');
const note=document.querySelector('#variant-note');
const el=(tag,attrs={},children=[])=>{const n=document.createElement(tag);for(const[k,v]of Object.entries(attrs)){if(v==null)continue;if(k==='text')n.textContent=String(v);else if(k==='class')n.className=v;else if(k==='checked')n.checked=!!v;else n.setAttribute(k,String(v))}for(const c of [].concat(children))if(c!=null)n.append(c?.nodeType?c:document.createTextNode(String(c)));return n};
const emit=value=>{response.textContent=JSON.stringify(value,null,2);response.dataset.emitted='true'};
const reset=()=>{response.textContent='Aucune réponse émise.';delete response.dataset.emitted;stage.replaceChildren()};
const header=(v,description)=>el('div',{class:'variant-header'},[el('p',{class:'eyebrow',text:v.id}),el('h2',{text:v.label}),el('p',{class:'variant-description',text:description})]);
const status=(text='')=>el('p',{class:'status',role:'status','aria-live':'polite',text});
const primary=(label,fn)=>{const b=el('button',{type:'button',class:'primary',text:label});b.addEventListener('click',fn);return b};
function isInteractiveTarget(t){return !!t.closest('button,select,input,a')}
function pointerDrag(node,{onStart,onMove,onDrop,onCancel,ignoreInteractive=false}){let drag=null;const end=(e,cancel=false)=>{if(!drag||e.pointerId!==drag.pointerId)return;try{node.releasePointerCapture?.(e.pointerId)}catch{}const current=drag;drag=null;(cancel?onCancel:onDrop)?.(current,e)};node.addEventListener('pointerdown',e=>{if(drag||e.button!==0)return;if(ignoreInteractive&&isInteractiveTarget(e.target)&&e.target!==node)return;e.preventDefault();drag={pointerId:e.pointerId,startX:e.clientX,startY:e.clientY,x:e.clientX,y:e.clientY,moved:false};node.setPointerCapture?.(e.pointerId);onStart?.(drag,e)});node.addEventListener('pointermove',e=>{if(!drag||e.pointerId!==drag.pointerId)return;drag.x=e.clientX;drag.y=e.clientY;if(Math.abs(drag.x-drag.startX)+Math.abs(drag.y-drag.startY)>5)drag.moved=true;onMove?.(drag,e)});node.addEventListener('pointerup',e=>end(e,false));node.addEventListener('pointercancel',e=>end(e,true))}
window.__LAB_CORE__={fixtures,variants,select,stage,response,note,el,emit,reset,header,status,primary,pointerDrag};
window.__LAB_RENDERERS__={};
})();
