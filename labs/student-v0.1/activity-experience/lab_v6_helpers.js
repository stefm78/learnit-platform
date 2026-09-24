(()=>{
'use strict';
const {el,emit,stage,header,status,primary,pointerDrag,shuffled}=window.__LAB_CORE__;

const setPressed=(map,id)=>map.forEach((node,key)=>node.setAttribute('aria-pressed',String(key===id)));
const clearPressed=map=>map.forEach(node=>node.setAttribute('aria-pressed','false'));
const keyActivate=(node,fn)=>node.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fn(e)}});
const targetAt=(x,y,selector,dragged)=>{for(const node of document.elementsFromPoint(x,y)){const target=node.closest?.(selector);if(target&&(!dragged||!target.contains(dragged)))return target}return null};
const clearEligibility=(root=stage)=>{root.querySelectorAll('.eligible-destination,.active-destination,.eligible-zone').forEach(n=>n.classList.remove('eligible-destination','active-destination','eligible-zone'))};
const markEligible=(nodes)=>nodes.forEach(n=>n.classList.add('eligible-destination'));
const markActive=(node)=>{stage.querySelectorAll('.active-destination').forEach(n=>n.classList.remove('active-destination'));if(node)node.classList.add('active-destination')};

window.__LAB_V6_HELPERS__={setPressed,clearPressed,keyActivate,targetAt,clearEligibility,markEligible,markActive};
})();
