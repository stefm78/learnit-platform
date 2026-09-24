(()=>{
'use strict';
const {fixtures,variants,select,note,reset,beginAttempt}=window.__LAB_CORE__;
function render(){reset();beginAttempt();const v=variants.find(x=>x.id===select.value)||variants[0];select.value=v.id;note.textContent=`${v.family} · ${v.id} · tentative ${window.__LAB_CORE__.attemptSeed}`;window.__LAB_RENDERERS__[v.id](v,structuredClone(fixtures[v.family]))}
variants.forEach(v=>{const o=document.createElement('option');o.value=v.id;o.textContent=`${v.id} — ${v.label}`;select.append(o)});select.addEventListener('change',render);select.value='lesson-a';render();window.__LAB__={fixtures,variants,render,get attemptSeed(){return window.__LAB_CORE__.attemptSeed}};
})();
