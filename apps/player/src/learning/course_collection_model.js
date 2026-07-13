(function(){
  'use strict';
  const schema='learnit.course_collection_model.rc386.v1';
  function courseId(course){return String(course&&course.title||'course').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');}
  function titleCaseToken(t){return String(t||'').charAt(0).toUpperCase()+String(t||'').slice(1).toLowerCase();}
  function humanizePackageLabel(packageId){
    const raw=String(packageId||'').trim(); if(!raw)return 'Imports';
    const tokens=raw.replace(/[_]+/g,'-').split('-').filter(Boolean).filter(t=>!/^rc\d+$/i.test(t)&&!/^v?\d+(?:\.\d+)*$/i.test(t)&&!/^(learnit|package|sample|importable|plus|content|demo|import)$/i.test(t));
    if(!tokens.length)return 'Imports';
    return tokens.map(titleCaseToken).join(' ').replace(/\bNombres Complexes\b/,'Nombres complexes').replace(/\bElectricite\b/,'Électricité');
  }
  function collectionMeta(course,index,lastAppliedRows){
    const id=courseId(course); const imported=!!(course&&(course.importedAt||course.importPackageId)); const packageId=course&&course.importPackageId||'';
    const recent=Array.isArray(lastAppliedRows)&&lastAppliedRows.some(r=>r&&r.courseId===id);
    if(imported)return {id:'import:'+packageId,key:'import:'+packageId,label:humanizePackageLabel(packageId),kind:'imported',recent,order:recent?0:2,colorIndex:index};
    if(/test|stress|rc\d+/i.test(String(course&&course.title||'')+' '+String(course&&course.contentVersion||'')))return {id:'tests',key:'tests',label:'Tests et contrôles',kind:'native',recent:false,order:4,colorIndex:index};
    return {id:'native',key:'native',label:'Parcours natifs',kind:'native',recent:false,order:1,colorIndex:index};
  }
  function buildCollections(courses,lastAppliedRows){
    const map=new Map();
    (courses||[]).forEach((course,index)=>{
      const meta=collectionMeta(course,index,lastAppliedRows);
      if(!map.has(meta.key))map.set(meta.key,Object.assign({},meta,{courses:[],activityCount:0}));
      const g=map.get(meta.key); g.courses.push(course); g.activityCount+=Array.isArray(course&&course.activities)?course.activities.length:0; g.recent=g.recent||meta.recent;
    });
    return [...map.values()].sort((a,b)=>a.order-b.order||a.label.localeCompare(b.label,'fr'));
  }
  function audit(){
    const courses=[{title:'Signaux électriques',activities:[{}]},{title:'Nombres complexes',importedAt:'x',importPackageId:'learnit-nombres-complexes-rc12',activities:[{},{}]}];
    const collections=buildCollections(courses,[{courseId:'nombres-complexes'}]);
    return {schema,ok:collections.length===2&&collections[0].kind==='imported'&&collections[0].label==='Nombres complexes'&&collections[1].label==='Parcours natifs',collections};
  }
  window.LearnItCourseCollectionModel=Object.freeze({schema,courseId,humanizePackageLabel,collectionMeta,buildCollections,audit});
})();
