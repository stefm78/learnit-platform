/* RC644 — pure surface, import and kit diagnostic engines. */

function jaccard(a,b){const A=new Set(a),B=new Set(b);const inter=[...A].filter(x=>B.has(x)).length;const union=new Set([...A,...B]).size||1;return inter/union;}

function buildSurfaceReport(runtime){
      const learn=buildLearningProjection(runtime), library=buildLibraryProjection(runtime), bilan=buildBilanProjection(runtime);
      const learnText=[learn.headline,learn.detail,learn.primary.label].join(' ');
      const libraryText=[library.title,library.sequence,library.objectives.join(' '),library.activityCount+' activités',library.primary.label].join(' ');
      const bilanText=[bilan.next,bilan.primary.label,String(bilan.last.correct),String((bilan.last.review||[]).length)].join(' ');
      const similarities={learnLibrary:jaccard(normalizeSurfaceText(learnText),normalizeSurfaceText(libraryText)),learnBilan:jaccard(normalizeSurfaceText(learnText),normalizeSurfaceText(bilanText)),libraryBilan:jaccard(normalizeSurfaceText(libraryText),normalizeSurfaceText(bilanText))};
      const primaryLabels=[learn.primary.label,library.primary.label,bilan.primary.label];
      const duplicatePrimary=primaryLabels.some((v,i)=>primaryLabels.indexOf(v)!==i);
      const visible=[learnText,libraryText,bilanText].join(' ');
      const weakHits=bannedSurfacePhrases.filter(p=>visible.includes(p));
      const items=[
        {code:'surface-intent-learn',ok:learn.surface==='learn'&&learn.primary.label!=='Aller à Apprendre',label:'Apprendre possède l’action immédiate'},
        {code:'surface-intent-library',ok:library.primary.label==='Aller à Apprendre',label:'Bibliothèque décrit le contenu et renvoie vers Apprendre'},
        {code:'surface-intent-bilan',ok:!!bilan.next&&bilan.primary.label!==library.primary.label,label:'Bilan produit un prochain pas distinct'},
        {code:'duplicate-primary',ok:!duplicatePrimary,label:'Actions primaires non dupliquées'},
        {code:'similarity-learn-library',ok:similarities.learnLibrary<0.60,label:'Apprendre/Bibliothèque non redondants',detail:String(similarities.learnLibrary.toFixed(2))},
        {code:'similarity-learn-bilan',ok:similarities.learnBilan<0.60,label:'Apprendre/Bilan non redondants',detail:String(similarities.learnBilan.toFixed(2))},
        {code:'similarity-library-bilan',ok:similarities.libraryBilan<0.60,label:'Bibliothèque/Bilan non redondants',detail:String(similarities.libraryBilan.toFixed(2))},
        {code:'weak-copy',ok:weakHits.length===0,label:'Aucune phrase faible bannie',detail:weakHits.join(' · ')}
      ];
      return {ok:items.every(i=>i.ok),learn,library,bilan,similarities,items,budgets:SURFACE_COPY_BUDGET,contract:SURFACE_OWNERSHIP};
    }

function buildFieldEvidenceReport(runtime){
      const gates=runtime.gates(); const surface=buildSurfaceReport(runtime); const courseQa=buildCourseQa(runtime.contentStore.allCourses()); const runtimeReport=buildRuntimeReport(runtime);
      const items=[
        {code:'runtime-clean',ok:runtimeReport.ok,label:'Runtime propre'},
        {code:'surface-owned',ok:surface.ok,label:'Surfaces différenciées'},
        {code:'course-library',ok:courseQa.ok&&courseQa.total>=3,label:'Bibliothèque multi-parcours valide'},
        {code:'state-truth',ok:gates.mirror&&gates.mirror.ok,label:'État Session / Apprendre cohérent'},
        {code:'content-only-patches',ok:RUNTIME_CONTRACT.patchMode==='content-only',label:'Correction par contenu uniquement'},
        {code:'no-forbidden-visible',ok:(gates.forbidden||[]).length===0,label:'Aucun marqueur technique visible'}
      ];
      return {ok:items.every(i=>i.ok),generatedAt:nowIso(),items,courseQa,gates,activeCourseId:runtime.contentStore.activeCourseId};
    }

function buildImportDiagnostics(runtime,text=runtime.contentStore.importDraft){
      const src=String(text||'');
      const items=[]; const repairs=[];
      const add=(ok,label,detail='',repair='')=>{items.push({ok,label,detail,repair}); if(!ok&&repair)repairs.push(repair);};
      if(!src.trim()){
        add(false,'Aucun JSON à analyser','Colle un parcours learnit-content-v2 ou un package learnit-course-package.','Utiliser Exemple import puis adapter le contenu.');
        return {ok:false,empty:true,items,repairs,preview:null,summary:'Aucun import à analyser'};
      }
      add(true,'Taille import',src.length>IMPORT_SIZE_ADVISORY_BYTES?`${src.length} caractères · au-dessus du seuil de confort ${IMPORT_SIZE_ADVISORY_BYTES}, accepté si le navigateur peut stocker le kit.`:`${src.length} caractères · accepté`, '');
      let payload=null;
      try{payload=JSON.parse(src);add(true,'JSON lisible','Syntaxe JSON valide.');}
      catch(e){add(false,'JSON lisible',String(e&&e.message||e),'Vérifier virgules, guillemets doubles, accolades et crochets.');return {ok:false,items,repairs,preview:null,summary:'JSON invalide'};}
      const normalized=runtime.contentStore.normalizeImportPayload(payload);
      add(!normalized.error,'Format racine',normalized.error||`${normalized.kind} · ${normalized.courses.length} parcours`,normalized.error?'Ajouter schemaVersion="learnit-content-v2" pour un parcours ou kind="learnit-course-package" avec courses[].':'');
      if(normalized.error)return {ok:false,items,repairs,preview:null,summary:'Format racine invalide'};
      const preview=runtime.contentStore.previewImport(src);
      add(!!preview.ok,'Prévisualisation import',preview.message||preview.error||'Import analysé',preview.ok?'':'Corriger les lignes HOLD ci-dessous avant import.');
      const builtInIds=new Set(CONTENT_LIBRARY.map(courseIdFromContent));
      const seen=new Set();
      for(const row of preview.rows||[]){
        const prefix=`Parcours ${row.title||row.courseId||'sans titre'}`;
        const renameDetail=row.autoRenamed?`Renommé automatiquement : ${row.originalCourseId} → ${row.courseId}`:row.courseId;
        const collisionNotes=[];if(row.builtInConflict)collisionNotes.push('conflit natif résolu');if(row.importedConflict)collisionNotes.push('doublon importé résolu');if(row.duplicateInBatch)collisionNotes.push('doublon package résolu');
        add(true,`${prefix} — identifiant`,collisionNotes.length?`${renameDetail} · ${collisionNotes.join(', ')}`:renameDetail,'');
        add(true,`${prefix} — doublon package`,row.duplicateInBatch?'Extension automatique appliquée.':'Identifiant unique','');
        add(!row.forbiddenJs,`${prefix} — contenu seulement`,row.forbiddenJs?'Le JSON ressemble à du comportement ou du JS.':'Aucun comportement injecté détecté',row.forbiddenJs?'Retirer function, =>, <scr'+'ipt>, javascript:, handlers onClick/onLoad, eval ou new Function.':'');
        const errors=(row.validation&&row.validation.errors)||[];
        add(errors.length===0,`${prefix} — schéma contenu`,errors.length?errors.join(' · '):`${row.activityCount} activité(s) valides`,errors.length?'Compléter les champs requis : id, type, question, réponses, tokens/pairs selon le type.':'');
        add(row.activityCount>=3,`${prefix} — richesse minimale`,`${row.activityCount} activité(s)`,row.activityCount<3?'Prévoir au moins 3 activités pour un parcours utilisable.':'');
        add(true,`${prefix} — volume activités`,row.activityCount>40?`${row.activityCount} activité(s) · accepté ; recommandation UX seulement : structurer en chapitres/parcours si la navigation devient lourde.`:`${row.activityCount} activité(s) · accepté`, '');
      }
      const ok=items.every(i=>i.ok);
      return {ok,items,repairs:[...new Set(repairs)],preview,summary:ok?'Import prêt':'Import à réparer'};
    }

function buildKitDiagnosticReport(runtime,text=runtime.contentStore.importDraft){
      const src=String(text||''),items=[];const rank={blocker:0,warning:1,advice:2};const add=(code,severity,message,correction,path='$',impact='')=>items.push({code,severity,message,correction,path,impact,ok:severity!=='blocker'});if(!src.trim()){add('kit-empty','blocker','Aucun JSON à analyser.','Choisir un ou plusieurs fichiers JSON.');return {schema:'learnit.kit_diagnostics.v2',ok:false,allClear:false,items,counters:{blocker:1,warning:0,advice:0},summary:'Import bloqué : aucun JSON',nextAction:'Choisir un fichier JSON.'};}
      let payload;try{payload=JSON.parse(src);}catch(e){add('json-invalid','blocker',String(e&&e.message||e),'Corriger la syntaxe JSON.');return {schema:'learnit.kit_diagnostics.v2',ok:false,allClear:false,items,counters:{blocker:1,warning:0,advice:0},summary:'Import bloqué : JSON invalide',nextAction:'Corriger la syntaxe JSON.'};}
      const normalized=runtime.contentStore.normalizeImportPayload(payload);if(normalized.error){add('root-format-invalid','blocker',normalized.error,'Utiliser un package learnit-course-package ou un parcours learnit-content-v2.');return {schema:'learnit.kit_diagnostics.v2',ok:false,allClear:false,items,counters:{blocker:1,warning:0,advice:0},summary:'Import bloqué : format racine invalide',nextAction:'Corriger le format racine.'};}
      const formats=new Set(['svg','png','jpeg','jpg','webp','gif']),roleSet=new Set(['concept_visual','question_stimulus','worked_example','misconception_fix','diagram_to_interpret','memory_anchor']),phaseRank={activation:0,diagnostic:0,comprehension:1,application:2,transfer:3,consolidation:4,validation:5,remediation:6};let totalActivities=0;for(let ci=0;ci<normalized.courses.length;ci++){const course=normalized.courses[ci]||{},cpath=`$.courses[${ci}]`,assets=[...(Array.isArray(course.assets)?course.assets:[])],assetMap=new Map(),usedAssets=new Set(),activityIds=new Set(),questionMap=new Map(),objectives=new Map();for(let ai=0;ai<assets.length;ai++){const a=assets[ai]||{},path=`${cpath}.assets[${ai}]`,id=String(a.id||'');if(!id){add('asset-id-missing','blocker','Un média ne possède pas d’identifiant.','Ajouter un id stable.',path,'Le média ne peut pas être référencé.');continue;}if(assetMap.has(id))add('asset-id-duplicate','blocker',`Média dupliqué : ${id}.`,'Rendre les identifiants uniques.',path);assetMap.set(id,a);const format=String(a.format||'').toLowerCase();if(!formats.has(format))add('asset-format-unsupported','blocker',`Format non supporté : ${format||'absent'}.`,'Utiliser svg, png, jpeg, webp ou gif.',path+'.format');if(!String(a.alt||'').trim())add('asset-alt-missing','warning',`Texte alternatif absent pour ${id}.`,'Ajouter un alt qui décrit l’information utile.',path+'.alt','Le média devient inaccessible ou ambigu.');if(!roleSet.has(String(a.pedagogical_role||a.pedagogicalRole||'')))add('asset-role-missing','warning',`Rôle pédagogique absent ou inconnu pour ${id}.`,'Choisir un rôle pédagogique du contrat.',path+'.pedagogical_role');const mediaSecurity=window.LearnItMediaSecurityModel;const mediaAudit=mediaSecurity&&typeof mediaSecurity.auditAsset==='function'?mediaSecurity.auditAsset(a):{ok:false,reason:'media-security-model-missing'};if(!mediaAudit.ok)add(format==='svg'?'svg-unsafe':'asset-source-unsafe','blocker',`Média non sûr détecté : ${id} (${mediaAudit.reason}).`,'Utiliser un SVG limité à l’allowlist, une image raster data: base64 ou une URL HTTPS sans identifiants.',path+'.data');if(String(a.data||'').length>750000)add('asset-large','warning',`Média volumineux : ${id}.`,'Compresser ou simplifier le média avant import.',path+'.data','Un média lourd peut saturer le stockage local.');}
        const activities=Array.isArray(course.activities)?course.activities:[];totalActivities+=activities.length;for(let ai=0;ai<activities.length;ai++){const a=activities[ai]||{},path=`${cpath}.activities[${ai}]`,id=String(a.id||''),objective=String(a.objective||'').trim(),phase=String(a.learning_phase||a.learningPhase||''),role=String(a.assessment_role||a.assessmentRole||''),q=String(a.question||'').toLowerCase().replace(/\s+/g,' ').trim();if(!id)add('activity-id-missing','blocker','Activité sans identifiant.','Ajouter un id stable.',path+'.id');else if(activityIds.has(id))add('activity-id-duplicate','blocker',`Activité dupliquée : ${id}.`,'Rendre les identifiants uniques.',path+'.id');activityIds.add(id);if(!objective)add('objective-missing','warning',`Objectif absent pour ${id||'activité'}.`,'Ajouter un objectif précis et stable.',path+'.objective','Le Bilan et la remédiation ne peuvent pas agréger correctement.');const list=objectives.get(objective)||[];list.push({a,path,phase,role,index:ai});if(objective)objectives.set(objective,list);if(q){if(questionMap.has(q))add('question-exact-duplicate','warning',`Question répétée à l’identique : ${a.question}`,'Varier la situation ou le raisonnement demandé.',path+'.question','La répétition mesure la mémoire de surface.');questionMap.set(q,path);}for(let mi=0;mi<(Array.isArray(a.media)?a.media:[]).length;mi++){const media=a.media[mi]||{},ref=String(media.assetId||'');if(!ref||!assetMap.has(ref))add('media-reference-missing','blocker',`Média introuvable : ${ref||'référence vide'}.`,'Déclarer l’asset ou corriger assetId.',`${path}.media[${mi}].assetId`);else usedAssets.add(ref);}if(!String(a.why||'').trim())add('feedback-why-missing','warning',`Explication absente pour ${id}.`,'Ajouter why pour expliquer la réponse.',path+'.why');if(!String(a.remediation||'').trim())add('remediation-text-missing','warning',`Remédiation absente pour ${id}.`,'Ajouter une piste différente de la correction.',path+'.remediation');if(ai>0){const prev=activities[ai-1]||{},pr=phaseRank[String(prev.learning_phase||prev.learningPhase||'')],cr=phaseRank[phase];if(Number.isFinite(pr)&&Number.isFinite(cr)&&cr+2<pr)add('phase-order-regression','advice',`Progression pédagogique irrégulière entre ${prev.id} et ${id}.`,'Réordonner activation, compréhension, application, transfert puis validation.',path+'.learning_phase');}}
        for(const [id] of assetMap)if(!usedAssets.has(id))add('asset-unused','advice',`Média non utilisé : ${id}.`,'Le référencer dans une activité ou le retirer.',cpath+'.assets','Les packages plus légers sont plus faciles à maintenir.');for(const [objective,rows] of objectives){const base=rows[0].path;if(rows.length<2)add('objective-single-evidence','advice',`Objectif couvert par une seule activité : ${objective}.`,'Prévoir une variante réellement différente.',base+'.objective');if(!rows.some(r=>r.role==='validation'))add('objective-no-validation','warning',`Aucune activité de validation pour : ${objective}.`,'Ajouter une activité assessment_role=validation.',base+'.assessment_role','La réussite n’est pas vérifiée sans aide.');if(!rows.some(r=>r.role==='remediation'||r.phase==='remediation'))add('objective-no-remediation','warning',`Aucune remédiation dédiée pour : ${objective}.`,'Ajouter une variante de remédiation différente.',base+'.assessment_role');if(activities.length>=6&&!rows.some(r=>r.phase==='transfer'))add('objective-no-transfer','advice',`Aucun transfert explicite pour : ${objective}.`,'Ajouter une situation nouvelle en learning_phase=transfer.',base+'.learning_phase');}const typeCount=new Set(activities.map(a=>a.type)).size;if(activities.length>=8&&typeCount<3)add('course-format-imbalance','warning',`Seulement ${typeCount} format(s) d’activité dans ${course.title||'le parcours'}.`,'Combiner rappel, discrimination, reconstruction et manipulation.',cpath+'.activities');}
      const preview=runtime.contentStore.previewImport(src,{collisionPolicy:runtime.contentStore.importCollisionPolicy});for(const b of preview.blockers||[])if(!items.some(i=>i.code===b.code&&i.path===b.path))add(b.code,'blocker',b.message,b.correction||'Corriger avant import.',b.path);for(const w of preview.warnings||[])add(w.code,'warning',w.message,w.correction||'Vérifier le volume.',w.path);items.sort((a,b)=>rank[a.severity]-rank[b.severity]||a.code.localeCompare(b.code));const counters={blocker:items.filter(i=>i.severity==='blocker').length,warning:items.filter(i=>i.severity==='warning').length,advice:items.filter(i=>i.severity==='advice').length};const ok=counters.blocker===0,allClear=ok&&counters.warning===0&&counters.advice===0;return {schema:'learnit.kit_diagnostics.v2',ok,allClear,items,counters,totalActivities,courses:normalized.courses.length,summary:ok?(allClear?'Kit prêt sans alerte':`Kit importable · ${counters.warning} avertissement(s) · ${counters.advice} conseil(s)`):`Import bloqué · ${counters.blocker} blocage(s)`,nextAction:ok?'Prévisualiser les changements puis importer.':(items.find(i=>i.severity==='blocker')||{}).correction||'Corriger le premier blocage.'};
    }

function collectUnknownFields(obj, allowed){
      if(!obj||typeof obj!=='object'||Array.isArray(obj))return [];
      return Object.keys(obj).filter(k=>!allowed.includes(k));
    }

function detectKitRootVersion(payload){
      const explicit = payload && (payload.schema_version || payload.schemaVersion || payload.contract_version || payload.contractVersion);
      if(explicit)return String(explicit);
      if(payload && payload.kind==='learnit-course-package')return 'learnit.import.v1-deduced';
      if(payload && payload.schemaVersion==='learnit-content-v2')return 'learnit-content-v2-legacy-single';
      return 'unknown';
    }

function normalizePedagogy(activity){
      const p = activity && activity.pedagogy && typeof activity.pedagogy==='object' ? activity.pedagogy : {};
      return {
        objective: activity.objective || p.objective || '',
        difficulty: activity.difficulty || p.difficulty || '',
        learning_phase: activity.learning_phase || activity.learningPhase || p.learning_phase || p.learningPhase || '',
        skills: activity.skills || p.skills || [],
        common_errors: activity.common_errors || activity.commonErrors || p.common_errors || p.commonErrors || [],
        feedback: activity.feedback || p.feedback || null
      };
    }
