(()=>{
'use strict';
const {fixtures,variants,select,note,reset}=window.__LAB_CORE__;
function render(){reset();const v=variants.find(x=>x.id===select.value)||variants[0];select.value=v.id;note.textContent=`${v.family} · ${v.id}`;window.__LAB_RENDERERS__[v.id](v,structuredClone(fixtures[v.family]))}
variants.forEach(v=>select.append(Object.assign(document.createElement('option'),{value:v.id,textContent:`${v.id} — ${v.label}`})));
select.addEventListener('change',render);select.value='lesson-a';render();
window.__LAB__={fixtures,variants,render};
})();
