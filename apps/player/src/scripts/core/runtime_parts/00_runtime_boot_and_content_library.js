
  (()=>{
    'use strict';
    const VERSION_LABEL = 'Learn-it RC718';
    const APP_BUILD = 'v5.718.0 — editable imported plan naming and persistence hardening candidate';
    document.title = VERSION_LABEL;
    const STORAGE_KEY = 'learnit_clean_state_v2';
    const JOURNAL_KEY = 'learnit_clean_journal_v2';
    const PATCH_KEY = 'learnit_content_patches_v2';
    const ACTIVE_COURSE_KEY = 'learnit_active_course_v1';
    const FIELD_EVIDENCE_KEY = 'learnit_field_evidence_v1';
    const IMPORTED_COURSES_KEY = 'learnit_imported_courses_v1';
    const IMPORT_HISTORY_KEY = 'learnit_import_history_v1';
    const IMPORT_LAST_APPLIED_KEY = 'learnit_import_last_applied_v1';
    const IMPORT_TRANSACTION_KEY = 'learnit_import_transaction_v1';
    const STATE_SCHEMA_VERSION = 4;
    const RECOVERY_REPORT_KEY = 'learnit_recovery_report_v1';
    const RESILIENCE_META_KEY = 'learnit_resilience_meta_v1';
    const IMPORT_SIZE_ADVISORY_BYTES = 260000; // advisory only: no hard cap on imported activities or courses
    const IMPORT_LOCAL_STORAGE_WARNING_COURSES = 40; // UI advisory only, never slices data
    const IMPORT_QUOTAS = Object.freeze({advisoryBytes:5000000,advisoryFiles:24,advisoryCourses:250,advisoryActivities:3000,hardFiles:100});
    const MAX_JOURNAL = 240;

    const storage = (()=>{
      const mem={};let backend=null,mode='memory-fallback',fault=null;const telemetry={reads:0,writes:0,removes:0,failures:0,lastFailure:null};
      try{const probe='learnit_storage_probe';window.localStorage.setItem(probe,'1');window.localStorage.removeItem(probe);backend=window.localStorage;mode='localStorage';}catch(e){backend=null;}
      const fail=(operation,key)=>{if(!fault||fault.operation!==operation||(fault.key&&fault.key!==key))return;const current=fault;fault=null;telemetry.failures+=1;telemetry.lastFailure={operation,key,name:current.name||'QuotaExceededError',at:new Date().toISOString()};throw new DOMException(current.message||'Synthetic storage fault',current.name||'QuotaExceededError');};
      const getItem=key=>{const k=String(key);telemetry.reads+=1;fail('getItem',k);try{return backend?(backend.getItem(k)||''):(Object.prototype.hasOwnProperty.call(mem,k)?mem[k]:'');}catch(error){telemetry.failures+=1;telemetry.lastFailure={operation:'getItem',key:k,name:error&&error.name||'Error',at:new Date().toISOString()};return '';}};
      const setItem=(key,value)=>{const k=String(key),v=String(value);telemetry.writes+=1;fail('setItem',k);try{if(backend)backend.setItem(k,v);else mem[k]=v;}catch(error){telemetry.failures+=1;telemetry.lastFailure={operation:'setItem',key:k,name:error&&error.name||'Error',at:new Date().toISOString()};throw error;}};
      const removeItem=key=>{const k=String(key);telemetry.removes+=1;fail('removeItem',k);try{if(backend)backend.removeItem(k);else delete mem[k];}catch(error){telemetry.failures+=1;telemetry.lastFailure={operation:'removeItem',key:k,name:error&&error.name||'Error',at:new Date().toISOString()};throw error;}};
      const dump=()=>{if(!backend)return {...mem};const out={};for(let i=0;i<backend.length;i++){const key=backend.key(i);if(key&&key.startsWith('learnit_'))out[key]=backend.getItem(key)||'';}return out;};
      const report=()=>Object.freeze({schema:'learnit.storage_adapter.rc685.v1',mode,...telemetry,lastFailure:telemetry.lastFailure?{...telemetry.lastFailure}:null});
      const injectFaultOnce=spec=>{fault={operation:String(spec&&spec.operation||'setItem'),key:String(spec&&spec.key||''),name:String(spec&&spec.name||'QuotaExceededError'),message:String(spec&&spec.message||'Synthetic storage fault')};return true;};
      return Object.freeze({getItem,setItem,removeItem,dump,report,injectFaultOnce});
    })();
    const deepClone = value => JSON.parse(JSON.stringify(value));
    const nowIso = () => new Date().toISOString();
    const weakPhrases = [
      'Tu as avancé', 'La recommandation reste limitée', 'On commence par ce qui est à revoir',
      'La suite immédiate reste visible', 'Fais un essai', 'Tu peux mettre en pause'
    ];
    const screenForbidden = ['[BLANK','un'+'defined','nu'+'ll','N'+'aN','[object '+'Object]','TO'+'DO','DE'+'BUG'];
    function hasForbiddenMarker(text, marker){const value=String(text||''); if(marker==='[BLANK')return /\[BLANK/i.test(value); if(marker==='undefined')return /(^|[^a-z])undefined([^a-z]|$)/i.test(value); if(marker==='null')return /(^|[^a-z])null([^a-z]|$)/i.test(value); if(marker==='NaN')return /(^|[^a-z])NaN([^a-z]|$)/.test(value); if(marker==='[object Object]')return value.includes('[object Object]'); if(marker==='TODO')return /(^|[^a-z])TODO([^a-z]|$)/i.test(value); if(marker==='DEBUG')return /(^|[^a-z])DEBUG([^a-z]|$)/i.test(value); return value.includes(marker);}
    const SURFACE_OWNERSHIP = Object.freeze({
      learn:{label:'Apprendre',question:'Que dois-je faire maintenant ?',owns:'action immédiate',primary:['start-session','resume-session','new-session'],forbidden:['catalogue détaillé','bilan détaillé','métadonnées longues']},
      library:{label:'Bibliothèque',question:'Que puis-je apprendre et choisir ?',owns:'carte du contenu',primary:['open-course-map'],forbidden:['reprise comme action principale permanente','bilan de séance']},
      bilan:{label:'Bilan',question:'Qu’ai-je compris, que revoir, que faire ensuite ?',owns:'diagnostic et prochain pas',primary:['start-review-session','new-session','learn'],forbidden:['copie de l’accueil','catalogue complet']}
    });
    const SURFACE_COPY_BUDGET = Object.freeze({learn:{maxBlocks:2,maxLines:8},library:{maxBlocks:4,maxLines:18},bilan:{maxBlocks:4,maxLines:16}});
    const bannedSurfacePhrases = weakPhrases.concat(['La suite immédiate','La recommandation reste','On commence par','Fais un essai']);


    const CONTENT_LIMITS = Object.freeze({questionMax:180,objectiveMax:120,remediationMax:220,choiceMax:90,activityMobileBudget:520});
    const RUNTIME_CONTRACT = Object.freeze({boot:1,titleWrites:1,mutationObserver:0,intervalTimers:0,sourceOfTruth:'AppState.session',patchMode:'content-only',multiParcours:'content-library',importMode:'explainable-diagnostics-preview-transactional-multifile-collision-policy-rollback',accessibility:'keyboard-focus-live-regions-inert-reduced-motion',resilience:'versioned-state-checkpoint-recovery'});

    const baseContent = Object.freeze({
      schemaVersion:'learnit-content-v2',
      contentVersion:'content-rc97.1',
      title:'Signaux électriques',
      sequence:'Tension, intensité, résistance',
      objectives:['calculer avec U = R × I','choisir un appareil de mesure','distinguer tension et intensité'],
      activities:[
        {id:'a1',type:'qcm',objective:'Appliquer U = R × I.',difficulty:'easy',learning_phase:'application',assessment_role:'practice',common_errors:['calculer avant d’écrire la formule','confondre U, R et I'],question:'Une résistance de 3 Ω est traversée par un courant de 2 A. Quelle est la tension ?',choices:['6 V','1,5 V','5 V','3 V'],answer:0,why:'U = R × I = 3 × 2 = 6 V.',remediation:'Refais le calcul en écrivant la formule avant les nombres.'},
        {id:'a2',type:'qcm',objective:'Associer grandeur et unité.',question:'Quelle est l’unité de la tension électrique ?',choices:['Volt','Ampère','Ohm','Watt'],answer:0,why:'La tension se mesure en volt, symbole V.',remediation:'Repère la grandeur : tension → volt.'},
        {id:'a3',type:'fill',objective:'Reconstruire la loi d’Ohm.',difficulty:'easy',learning_phase:'comprehension',assessment_role:'remediation',common_errors:['calculer avant d’écrire la formule','confondre U, R et I'],question:'Complète la relation.',parts:['U = ',0,' × ',1],tokens:['R','I','P','t'],answer:['R','I'],sentence:'U = R × I',why:'La tension U dépend de la résistance R et de l’intensité I.',remediation:'Place les grandeurs de la loi d’Ohm : R puis I.'},
        {id:'a4',type:'qcm',objective:'Reconnaître une mesure d’intensité.',question:'Quel appareil mesure l’intensité du courant ?',choices:['Ampèremètre','Voltmètre','Ohmmètre','Chronomètre'],answer:0,why:'L’intensité se mesure avec un ampèremètre, placé en série.',remediation:'Associe intensité et ampèremètre : même racine.'},
        {id:'a5',type:'fill',objective:'Identifier l’appareil adapté.',question:'Complète la phrase.',parts:['La tension se mesure avec un ',0,' en ',1,'.'],tokens:['voltmètre','dérivation','ampèremètre','série'],answer:['voltmètre','dérivation'],sentence:'La tension se mesure avec un voltmètre en dérivation.',why:'Un voltmètre compare deux points du circuit : il se branche en dérivation.',remediation:'Tension : voltmètre. Branchement : dérivation.'},
        {id:'a6',type:'matching',objective:'Relier grandeur, symbole et unité.',question:'Associe chaque grandeur à son unité.',pairs:[['Tension','volt'],['Intensité','ampère'],['Résistance','ohm']],why:'Chaque grandeur possède son unité propre.',remediation:'Commence par les couples les plus sûrs : tension → volt, résistance → ohm.'},
        {id:'a7',type:'fill',objective:'Relier résistance et unité.',question:'Complète la phrase.',parts:['La résistance se note ',0,' et se mesure en ',1,'.'],tokens:['R','ohm','U','volt'],answer:['R','ohm'],sentence:'La résistance se note R et se mesure en ohm.',why:'Le symbole de la résistance est R ; son unité est l’ohm, noté Ω.',remediation:'Résistance commence par R ; son unité est l’ohm.'},
        {id:'a8',type:'qcm',objective:'Choisir le bon branchement.',question:'Pour mesurer une intensité, l’ampèremètre se place…',choices:['en série','en dérivation','hors du circuit','en parallèle avec le générateur'],answer:0,why:'Le courant à mesurer doit traverser l’ampèremètre.',remediation:'Si l’appareil doit être traversé par le courant, il se place en série.'},
        {id:'a9',type:'order',objective:'Ordonner une résolution.',difficulty:'medium',learning_phase:'remediation',assessment_role:'remediation',common_errors:['calculer avant d’écrire la formule','confondre U, R et I'],question:'Remets les étapes dans l’ordre pour calculer une tension.',tokens:['Écrire U = R × I','Remplacer R et I','Calculer','Ajouter l’unité'],answer:['Écrire U = R × I','Remplacer R et I','Calculer','Ajouter l’unité'],why:'La méthode évite les calculs sans unité.',remediation:'Commence par la formule, termine par l’unité.'},
        {id:'a10',type:'qcm',objective:'Distinguer tension et intensité.',question:'Quelle affirmation est correcte ?',choices:['La tension se mesure entre deux points.','L’intensité se mesure en volt.','La résistance se note I.','Un voltmètre se place en série.'],answer:0,why:'La tension est une différence entre deux points du circuit.',remediation:'Cherche l’affirmation qui parle de deux points : c’est la tension.'}
      ]
    });


    const electricityPowerContent = Object.freeze({
      schemaVersion:'learnit-content-v2',
      contentVersion:'content-power-rc125.1',
      title:'Puissance électrique',
      sequence:'Puissance, énergie, unités',
      objectives:['calculer avec P = U × I','relier puissance et énergie','interpréter watt et kilowattheure'],
      activities:[
        {id:'p1',type:'qcm',objective:'Appliquer P = U × I.',difficulty:'easy',learning_phase:'application',assessment_role:'practice',common_errors:['confondre puissance et énergie','utiliser la mauvaise relation'],question:'Une lampe reçoit 12 V et 0,5 A. Quelle est sa puissance ?',choices:['6 W','24 W','12,5 W','0,04 W'],answer:0,why:'P = U × I = 12 × 0,5 = 6 W.',remediation:'Écris P = U × I puis remplace les valeurs.'},
        {id:'p2',type:'fill',objective:'Reconstruire la relation de puissance.',difficulty:'easy',learning_phase:'remediation',assessment_role:'remediation',common_errors:['confondre puissance et énergie','utiliser la mauvaise relation'],question:'Complète la relation.',parts:['P = ',0,' × ',1],tokens:['U','I','R','t'],answer:['U','I'],sentence:'P = U × I',why:'La puissance dépend de la tension et de l’intensité.',remediation:'Puissance : tension fois intensité.'},
        {id:'p3',type:'qcm',objective:'Identifier l’unité de puissance.',question:'Quelle est l’unité de la puissance électrique ?',choices:['Watt','Volt','Ampère','Ohm'],answer:0,why:'La puissance se mesure en watt, symbole W.',remediation:'Puissance commence souvent par P, unité watt W.'},
        {id:'p4',type:'matching',objective:'Associer grandeur et unité.',question:'Associe chaque grandeur à son unité.',pairs:[['Puissance','watt'],['Énergie','joule'],['Tension','volt']],why:'Chaque grandeur se lit avec son unité propre.',remediation:'Commence par puissance → watt.'},
        {id:'p5',type:'qcm',objective:'Relier énergie et durée.',question:'À puissance constante, si la durée double, l’énergie consommée…',choices:['double','reste identique','est divisée par deux','devient nulle'],answer:0,why:'Énergie = puissance × durée.',remediation:'Plus un appareil fonctionne longtemps, plus il consomme.'},
        {id:'p6',type:'order',objective:'Ordonner un calcul d’énergie.',question:'Remets les étapes dans l’ordre pour calculer une énergie.',tokens:['Identifier la puissance','Identifier la durée','Multiplier','Ajouter l’unité'],answer:['Identifier la puissance','Identifier la durée','Multiplier','Ajouter l’unité'],why:'La méthode évite de mélanger nombres et unités.',remediation:'Commence par repérer les grandeurs utiles.'}
      ]
    });
    const circuitsContent = Object.freeze({
      schemaVersion:'learnit-content-v2',
      contentVersion:'content-circuits-rc125.1',
      title:'Circuits électriques',
      sequence:'Série, dérivation, mesures',
      objectives:['distinguer série et dérivation','prévoir une mesure','raisonner sur le trajet du courant'],
      activities:[
        {id:'c1',type:'qcm',objective:'Reconnaître un circuit en série.',question:'Dans un circuit en série, les dipôles sont placés…',choices:['sur une seule boucle','sur plusieurs branches','hors du circuit','sans générateur'],answer:0,why:'En série, il n’y a qu’un chemin pour le courant.',remediation:'Cherche s’il existe une seule boucle.'},
        {id:'c2',type:'qcm',objective:'Reconnaître une dérivation.',question:'Dans un circuit en dérivation, le courant peut…',choices:['se répartir dans plusieurs branches','disparaître','traverser aucun dipôle','changer d’unité'],answer:0,why:'Une dérivation crée plusieurs chemins possibles.',remediation:'Dérivation signifie branches.'},
        {id:'c3',type:'fill',objective:'Compléter le vocabulaire du circuit.',question:'Complète la phrase.',parts:['Un circuit en dérivation contient plusieurs ',0,'.'],tokens:['branches','unités','résistances','volts'],answer:['branches'],sentence:'Un circuit en dérivation contient plusieurs branches.',why:'Les branches sont les chemins séparés du circuit.',remediation:'Associe dérivation avec branches.'},
        {id:'c4',type:'matching',objective:'Relier mesure et branchement.',question:'Associe l’appareil à son branchement.',pairs:[['Voltmètre','dérivation'],['Ampèremètre','série'],['Ohmmètre','hors tension']],why:'Chaque appareil impose son mode de branchement.',remediation:'Voltmètre : aux bornes ; ampèremètre : traversé.'},
        {id:'c5',type:'qcm',objective:'Prévoir une panne simple.',question:'Dans un circuit en série, si une lampe est débranchée, les autres lampes…',choices:['s’éteignent','brillent plus','ne changent pas','deviennent des générateurs'],answer:0,why:'La boucle est coupée, le courant ne circule plus.',remediation:'En série, couper un point coupe toute la boucle.'},
        {id:'c6',type:'order',objective:'Analyser un circuit.',question:'Ordonne les étapes pour analyser un montage.',tokens:['Repérer le générateur','Identifier les branches','Placer les appareils de mesure','Interpréter les valeurs'],answer:['Repérer le générateur','Identifier les branches','Placer les appareils de mesure','Interpréter les valeurs'],why:'On comprend le circuit avant d’interpréter les mesures.',remediation:'Commence toujours par la structure du circuit.'}
      ]
    });
    const CONTENT_LIBRARY = Object.freeze([baseContent, electricityPowerContent, circuitsContent]);
    function getCourseById(courseId){return CONTENT_LIBRARY.find(c=>courseId===courseIdFromContent(c))||baseContent;}
    function courseSlugFromTitle(content){return String(content&&content.title||'course').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'course';}
    function courseIdFromContent(content){const stable=String(content&&(content.localCourseId||content.courseId)||'').trim();return stable||courseSlugFromTitle(content);}
    function buildCourseQa(courses=CONTENT_LIBRARY){const rows=courses.map(c=>({courseId:courseIdFromContent(c),title:c.title,validation:(new ContentValidator()).validate(c),activities:c.activities.length,imported:!!c.importedAt}));return {ok:rows.every(r=>r.validation.ok),rows,total:rows.length,imported:rows.filter(r=>r.imported).length};}
