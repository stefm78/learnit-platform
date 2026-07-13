/* RC676 — AI contract and pedagogical quality diagnostics with truthful score ceilings. */

function buildAiKitContractDiagnostics(runtime,text=runtime.contentStore.importDraft){
      const src=String(text||'');
      const items=[]; const repairs=[];
      const add=(severity,label,detail='',repair='',path='')=>{
        const ok = severity!=='blocker';
        const item={ok,severity,label,detail,repair,path}; items.push(item);
        if(severity==='blocker'&&repair)repairs.push(repair);
      };
      const contract={name:'Learn-it AI Kit Contract',version:'learnit.import.v1.1-compatible',policy:'technical-blockers-only; pedagogical metadata optional'};
      if(!src.trim()){
        add('blocker','Aucun kit à contrôler','Colle un JSON généré par le skill ou un package Learn-it.','Coller un package kind="learnit-course-package" ou un parcours learnit-content-v2.','$');
        return {ok:false,contract,items,blockers:1,warnings:0,infos:0,repairs,summary:'Aucun kit'};
      }
      if(src.length>IMPORT_SIZE_ADVISORY_BYTES)add('warning','Taille élevée',`${src.length} caractères · seuil de confort ${IMPORT_SIZE_ADVISORY_BYTES}, non bloquant.`,'Découper seulement si le navigateur ou l’ergonomie locale deviennent insuffisants.','$');
      let payload=null;
      try{payload=JSON.parse(src);add('info','JSON lisible','Syntaxe JSON valide.','','$');}
      catch(e){add('blocker','JSON invalide',String(e&&e.message||e),'Corriger la syntaxe JSON : virgules, guillemets doubles, accolades/crochets.','$');return {ok:false,contract,items,blockers:items.filter(i=>i.severity==='blocker').length,warnings:0,infos:items.filter(i=>i.severity==='info').length,repairs,summary:'JSON invalide'};}
      const rootVersion=detectKitRootVersion(payload);
      if(rootVersion==='learnit.import.v1-deduced' || rootVersion==='learnit-content-v2-legacy-single')add('warning','Version de contrat déduite',rootVersion,'Ajouter schema_version="learnit.import.v1" au package pour tracer le contrat.','$');
      else if(rootVersion==='unknown')add('blocker','Version / format racine non reconnu','Aucune version ou racine Learn-it détectée.','Utiliser kind="learnit-course-package" avec courses[] ou un parcours schemaVersion="learnit-content-v2".','$');
      else add('info','Version de contrat déclarée',rootVersion,'','$');
      const normalized=runtime.contentStore.normalizeImportPayload(payload);
      if(normalized.error){add('blocker','Format racine non importable',normalized.error,'Ajouter kind="learnit-course-package" avec courses[] ou fournir un parcours learnit-content-v2.','$');}
      const rootAllowed=['kind','schema_version','schemaVersion','contract_version','contractVersion','packageId','package_id','source','source_title','sourceTitle','generator','generation_report','generationReport','assets','courses'];
      const rootUnknown=collectUnknownFields(payload,rootAllowed);
      if(rootUnknown.length)add('warning','Champs racine inconnus',rootUnknown.slice(0,8).join(', '),'Conserver seulement si utile au skill ; l’application les ignorera.','$');
      const report=payload && (payload.generation_report || payload.generationReport);
      if(!report)add('warning','Rapport de génération absent','Utile pour les kits produits par IA : couverture source, limites connues, validation IA.','Ajouter generation_report avec source_coverage, activity_count, validation_status.','$.generation_report');
      else add('info','Rapport de génération présent','Bloc audit IA détecté.','','$.generation_report');
      const rootAssets=Array.isArray(payload&&payload.assets)?payload.assets:[];
      if(rootAssets.length)add('info','Assets pédagogiques déclarés',`${rootAssets.length} asset(s) au niveau package`,'','$.assets');
      const courses=(normalized && normalized.courses)||[];
      if(!courses.length)add('blocker','Aucun parcours détecté','Le package ne contient pas courses[] exploitable.','Ajouter un tableau courses avec au moins un parcours.','$.courses');
      const allowedCourse=['schemaVersion','schema_version','contentVersion','content_version','title','sequence','objectives','assets','activities','importedAt','importPackageId','pedagogy','difficulty','learning_phase','skills','generation_report','generationReport','package_generation_report','packageGenerationReport','library_presentation','libraryPresentation'];
      const allowedActivity=['id','type','objective','question','prompt','front','back','choices','answer','why','remediation','tokens','parts','sentence','pairs','media','pedagogy','difficulty','learning_phase','learningPhase','skills','common_errors','commonErrors','feedback','hint','hints','assessment_role','assessmentRole','transfer_probe','transfer_distance','variant_of'];
      const types=['qcm','fill','matching','order','flashcard'];
      let totalActivities=0; let optionalPedagogyMissing=0; let longActivities=0; let unsupported=0;
      courses.forEach((course,ci)=>{
        const cpath=`$.courses[${ci}]`;
        const title=course && course.title ? String(course.title) : `Parcours ${ci+1}`;
        if(!course || typeof course!=='object') {add('blocker',`${title} — objet parcours invalide`,'Le parcours n’est pas un objet JSON.','Remplacer par un objet parcours complet.',cpath); return;}
        const cver=course.schemaVersion || course.schema_version;
        if(!cver)add('warning',`${title} — schemaVersion absent`,'Le parcours sera évalué comme contenu legacy compatible.','Ajouter schemaVersion="learnit-content-v2" dans chaque parcours.',`${cpath}.schemaVersion`);
        else if(cver!=='learnit-content-v2')add('warning',`${title} — schemaVersion non standard`,String(cver),'Vérifier la compatibilité ou fournir un adaptateur.',`${cpath}.schemaVersion`);
        if(!course.title)add('blocker',`${title} — titre absent`,'Le titre sert à la Bibliothèque et à l’identifiant import.','Ajouter title explicite.',`${cpath}.title`);
        if(!Array.isArray(course.activities)||!course.activities.length)add('blocker',`${title} — activités absentes`,'activities[] doit contenir au moins une activité.','Ajouter activities[].',`${cpath}.activities`);
        const cUnknown=collectUnknownFields(course,allowedCourse);
        if(cUnknown.length)add('warning',`${title} — champs parcours inconnus`,cUnknown.slice(0,8).join(', '),'Ces champs seront ignorés par l’application actuelle.',cpath);
        const objectives=Array.isArray(course.objectives)?course.objectives:[];
        if(!objectives.length)add('warning',`${title} — objectifs de parcours absents`,'Le Bilan et la remédiation seront moins actionnables.','Ajouter objectives[] avec 2 à 6 objectifs clairs.',`${cpath}.objectives`);
        const acts=Array.isArray(course.activities)?course.activities:[];
        totalActivities+=acts.length;
        const ids=new Set(); const counts={};
        acts.forEach((a,ai)=>{
          const apath=`${cpath}.activities[${ai}]`;
          if(!a || typeof a!=='object'){add('blocker',`${title} — activité ${ai+1} invalide`,'L’activité n’est pas un objet.','Remplacer par un objet activité.',apath);return;}
          const label=a.id?`${title} / ${a.id}`:`${title} / activité ${ai+1}`;
          if(!a.id)add('blocker',`${label} — id absent`,'Chaque activité doit avoir un id stable.','Ajouter un id unique et stable.',`${apath}.id`);
          else if(ids.has(a.id))add('blocker',`${label} — id dupliqué`,String(a.id),'Renommer l’activité pour obtenir un id unique dans le parcours.',`${apath}.id`);
          ids.add(a.id);
          if(!a.type){add('blocker',`${label} — type absent`,'Types supportés : qcm, fill, matching, order, flashcard.','Ajouter type.',`${apath}.type`);}
          else if(!types.includes(a.type)){unsupported++; add('blocker',`${label} — type non supporté`,String(a.type),'Mapper vers qcm/fill/matching/order/flashcard ou attendre un futur renderer.',`${apath}.type`);}
          else counts[a.type]=(counts[a.type]||0)+1;
          if(!a.question && !a.prompt)add('blocker',`${label} — consigne absente`,'Le renderer actuel attend question ; prompt est toléré comme intention future mais non importé automatiquement.','Ajouter question explicite.',`${apath}.question`);
          if(a.prompt && !a.question)add('blocker',`${label} — alias prompt non importable seul`,'Le skill utilise prompt, mais l’application actuelle consomme question.','Copier prompt vers question avant import.',`${apath}.question`);
          const aUnknown=collectUnknownFields(a,allowedActivity);
          if(aUnknown.length)add('warning',`${label} — champs activité inconnus`,aUnknown.slice(0,8).join(', '),'OK si utiles au skill ; ignorés par le renderer actuel.',apath);
          const ped=normalizePedagogy(a);
          if(!ped.objective){optionalPedagogyMissing++; add('warning',`${label} — objectif pédagogique absent`,'L’activité fonctionnera, mais le Bilan sera moins précis.','Ajouter objective ou pedagogy.objective.',`${apath}.objective`);}
          if(!ped.difficulty)add('warning',`${label} — difficulté absente`,'Champ optionnel utile pour équilibrer les reprises.','Ajouter difficulty: easy | medium | advanced | expert.',`${apath}.difficulty`);
          if(!ped.learning_phase)add('warning',`${label} — phase d’apprentissage absente`,'Champ optionnel utile pour distinguer compréhension, application, transfert, remédiation.','Ajouter learning_phase optionnel.',`${apath}.learning_phase`);
          if(!a.why && !(ped.feedback&&ped.feedback.success))add('warning',`${label} — feedback succès faible`,'L’apprenant saura si c’est juste, mais pas pourquoi.','Ajouter why ou feedback.success.',`${apath}.why`);
          if(!a.remediation && !(ped.feedback&&ped.feedback.error))add('warning',`${label} — remédiation absente`,'Les reprises ciblées seront moins utiles.','Ajouter remediation ou feedback.error.',`${apath}.remediation`);
          const serialized=JSON.stringify(a);
          if(serialized.length>CONTENT_LIMITS.activityMobileBudget*4){longActivities++; add('warning',`${label} — activité dense mobile`,`${serialized.length} caractères sérialisés`,'Découper ou alléger la consigne/options pour téléphone.',apath);}
          if(a.type==='qcm'){
            if(!Array.isArray(a.choices)||a.choices.length<2)add('blocker',`${label} — QCM sans choix`,'choices[] doit contenir au moins 2 choix.','Ajouter choices[].',`${apath}.choices`);
            if(!Number.isInteger(a.answer))add('blocker',`${label} — réponse QCM invalide`,'answer doit être l’index numérique du bon choix.','Ajouter answer numérique 0..n-1.',`${apath}.answer`);
          }
          if(a.type==='fill'){
            if(!Array.isArray(a.tokens)||!Array.isArray(a.answer)||!Array.isArray(a.parts))add('blocker',`${label} — fill incomplet`,'tokens[], answer[] et parts[] sont requis.','Compléter tokens, answer, parts.',apath);
          }
          if(a.type==='matching'){
            if(!Array.isArray(a.pairs)||a.pairs.length<2)add('blocker',`${label} — matching incomplet`,'pairs[] doit contenir au moins deux paires.','Ajouter pairs: [{left,right}, ...].',`${apath}.pairs`);
          }
          if(a.type==='order'){
            if(!Array.isArray(a.tokens)||!Array.isArray(a.answer)||a.tokens.length!==a.answer.length)add('blocker',`${label} — order incomplet`,'tokens[] et answer[] doivent avoir la même longueur.','Compléter tokens/answer dans l’ordre attendu.',apath);
          }
          if(a.type==='flashcard'){
            if(!String(a.answer||a.back||'').trim())add('blocker',`${label} — flashcard sans réponse`,'answer ou back doit contenir la réponse affichée après rappel.','Ajouter answer ou back.',`${apath}.answer`);
          }
          if(Array.isArray(a.media)){
            a.media.forEach((m,mi)=>{if(!m.assetId)add('blocker',`${label} — media sans assetId`,'Chaque média doit référencer assets[].','Ajouter assetId.',`${apath}.media[${mi}].assetId`);});
          }
        });
        const typeKinds=Object.keys(counts).length;
        if(acts.length>=4 && typeKinds<2)add('warning',`${title} — variété d’activités faible`,Object.entries(counts).map(([k,v])=>`${k}:${v}`).join(' · ')||'aucun type','Prévoir au moins deux formats pour soutenir l’apprentissage.',cpath);
      });
      if(totalActivities)add('info','Volume total analysé',`${totalActivities} activité(s) · ${courses.length} parcours`, '', '$');
      const blockers=items.filter(i=>i.severity==='blocker').length;
      const warnings=items.filter(i=>i.severity==='warning').length;
      const infos=items.filter(i=>i.severity==='info').length;
      const summary=blockers?`${blockers} blocage(s), ${warnings} alerte(s)`:`Contrat importable · ${warnings} alerte(s) non bloquante(s)`;
      return {ok:blockers===0,contract,items,blockers,warnings,infos,repairs:[...new Set(repairs)],summary,stats:{courses:courses.length,totalActivities,optionalPedagogyMissing,longActivities,unsupported}};
    }

function buildAiKitContractPanel(runtime,text=runtime.contentStore.importDraft){
      const d=buildAiKitContractDiagnostics(runtime,text);
      const rows=d.items.slice(0,18).map(i=>{
        const cls=i.severity==='blocker'?'blocker':(i.severity==='warning'?'warning':'info');
        const tag=i.severity==='blocker'?'BLOQUE':(i.severity==='warning'?'ALERTE':'INFO');
        return `<div class="qa-item ${cls}"><b class="severity">${tag}</b><span><strong>${escapeHtml(i.label)}</strong>${i.detail?`<br><span class="tiny">${escapeHtml(i.detail)}</span>`:''}${i.path?`<br><span class="tiny">Chemin : ${escapeHtml(i.path)}</span>`:''}${i.repair?`<br><span class="tiny">Correction : ${escapeHtml(i.repair)}</span>`:''}</span></div>`;
      }).join('');
      return `<div class="contract-panel"><div class="contract-head"><div><h3>Contrat kit IA</h3><div class="contract-summary">${escapeHtml(d.summary)} · Champs pédagogiques optionnels : alertes, pas rejet.</div></div><span class="badge ${d.ok?'ok':'warn'}">${d.ok?'IMPORTABLE':'À réparer'}</span></div><div class="import-preview-grid"><div class="import-stat"><b>${d.blockers}</b><span>blocages</span></div><div class="import-stat"><b>${d.warnings}</b><span>alertes</span></div><div class="import-stat"><b>${d.stats?d.stats.totalActivities:0}</b><span>activités</span></div><div class="import-stat"><b>${d.stats?d.stats.optionalPedagogyMissing:0}</b><span>objectifs absents</span></div></div><div class="qa-list">${rows||'<p class="tiny">Aucun item à afficher.</p>'}</div></div>`;
    }

function buildPedagogicalQualityDiagnostics(runtime,text=runtime.contentStore.importDraft){
      const src=String(text||'');
      const items=[]; const recommendations=[];
      const add=(severity,label,detail='',recommendation='',path='')=>{items.push({ok:severity!=='warning',severity,label,detail,recommendation,path}); if(recommendation)recommendations.push(recommendation);};
      let payload=null; let courses=[]; let source='import-draft';
      if(src.trim()){
        try{payload=JSON.parse(src);}catch(e){return {ok:true,score:null,grade:'NA',items:[{ok:false,severity:'warning',label:'Qualité pédagogique non évaluée',detail:'JSON non lisible : '+String(e&&e.message||e),recommendation:'Corriger la syntaxe JSON avant diagnostic pédagogique.',path:'$'}],recommendations:['Corriger la syntaxe JSON avant diagnostic pédagogique.'],stats:{courses:0,totalActivities:0},summary:'Diagnostic pédagogique impossible : JSON invalide'};}
        const normalized=runtime.contentStore.normalizeImportPayload(payload);
        if(normalized && !normalized.error){courses=normalized.courses||[];}else{return {ok:true,score:null,grade:'NA',items:[{ok:false,severity:'warning',label:'Qualité pédagogique non évaluée',detail:normalized.error||'Format racine non reconnu',recommendation:'Corriger le contrat technique avant diagnostic pédagogique.',path:'$'}],recommendations:['Corriger le contrat technique avant diagnostic pédagogique.'],stats:{courses:0,totalActivities:0},summary:'Diagnostic pédagogique impossible : contrat technique invalide'};}
      }else{
        courses=[runtime.contentStore.content]; source='active-course';
        add('info','Source analysée','Aucun import collé : diagnostic sur le parcours actif.','Coller un kit pour diagnostiquer le package avant import.','$');
      }
      const typeCounts={}; const difficultyCounts={}; const phaseCounts={}; const objectiveCounts={};
      let totalActivities=0, missingObjective=0, missingDifficulty=0, missingPhase=0, missingSuccess=0, missingRemediation=0, longPrompt=0, longChoice=0, tooFew=0, courseObjectivesMissing=0, commonErrorsPresent=0, assessmentRolePresent=0, nearDuplicateCount=0, exactDuplicateCount=0, weakVariantCount=0;
      const difficultyRank={easy:1,medium:2,advanced:3,expert:4,facile:1,moyen:2,avancé:3,avance:3,difficile:3};
      const allowedPhases=['activation','comprehension','compréhension','application','transfer','transfert','remediation','remédiation','consolidation','diagnostic','validation'];
      const normalizeLower=v=>String(v||'').trim().toLowerCase();
      courses.forEach((course,ci)=>{
        const title=course&&course.title?String(course.title):`Parcours ${ci+1}`;
        const cpath=`$.courses[${ci}]`;
        const acts=Array.isArray(course&&course.activities)?course.activities:[];
        totalActivities+=acts.length;
        if(acts.length>0 && acts.length<4){tooFew++; add('warning',`${title} — volume pédagogique faible`,`${acts.length} activité(s)`, 'Prévoir au moins 4 activités si le parcours doit former une vraie mini-séquence.', cpath);}
        const courseObjectives=Array.isArray(course&&course.objectives)?course.objectives.filter(Boolean):[];
        if(!courseObjectives.length){courseObjectivesMissing++; add('warning',`${title} — objectifs de parcours absents`,'Le Bilan et la reprise ciblée auront moins de repères.', 'Ajouter 2 à 6 objectifs de parcours clairs.', `${cpath}.objectives`);}
        let previousRank=0; let backwardJumps=0;
        const localTypes={}; const localPhases={};
        acts.forEach((a,ai)=>{
          const apath=`${cpath}.activities[${ai}]`;
          const label=a&&a.id?`${title} / ${a.id}`:`${title} / activité ${ai+1}`;
          if(!a||typeof a!=='object')return;
          typeCounts[a.type]=(typeCounts[a.type]||0)+1; localTypes[a.type]=(localTypes[a.type]||0)+1;
          const ped=normalizePedagogy(a);
          const objective=String(ped.objective||'').trim();
          if(!objective){missingObjective++; add('warning',`${label} — objectif non explicite`,'L’activité fonctionne, mais la reprise ciblée sera moins précise.', 'Ajouter objective ou pedagogy.objective.', `${apath}.objective`);} else {objectiveCounts[objective]=(objectiveCounts[objective]||0)+1;}
          const diff=normalizeLower(ped.difficulty);
          if(!diff){missingDifficulty++;} else {difficultyCounts[diff]=(difficultyCounts[diff]||0)+1; const rank=difficultyRank[diff]||0; if(rank&&previousRank&&rank+1<previousRank)backwardJumps++; if(rank)previousRank=rank;}
          const phase=normalizeLower(ped.learning_phase);
          if(!phase){missingPhase++;} else {phaseCounts[phase]=(phaseCounts[phase]||0)+1; localPhases[phase]=(localPhases[phase]||0)+1; if(!allowedPhases.includes(phase))add('warning',`${label} — phase non standard`,phase,'Utiliser activation, comprehension, application, transfer, remediation, consolidation, diagnostic ou validation.',`${apath}.learning_phase`);}
          if(!a.why && !(ped.feedback&&ped.feedback.success)){missingSuccess++;}
          if(!a.remediation && !(ped.feedback&&ped.feedback.error)){missingRemediation++;}
          if(Array.isArray(ped.common_errors)&&ped.common_errors.length)commonErrorsPresent++;
          if(a.assessment_role || a.assessmentRole)assessmentRolePresent++;
          const q=String(a.question||a.prompt||''); if(q.length>220){longPrompt++; add('warning',`${label} — consigne longue`,`${q.length} caractères`, 'Découper la consigne ou la transformer en étape guidée sur mobile.', `${apath}.question`);}
          if(Array.isArray(a.choices)){a.choices.forEach((c,idx)=>{if(String(c).length>130){longChoice++; add('warning',`${label} — choix QCM long`, `choix ${idx+1} · ${String(c).length} caractères`, 'Réduire le choix ou déplacer l’explication dans le feedback.', `${apath}.choices[${idx}]`);}});}
        });
        const varietyModel=window.LearnItVarietyModel;const varietyAudit=varietyModel&&typeof varietyModel.auditCourse==='function'?varietyModel.auditCourse(course):null;
        if(varietyAudit){
          exactDuplicateCount+=varietyAudit.exactDuplicates.length;nearDuplicateCount+=varietyAudit.nearDuplicates.length;weakVariantCount+=varietyAudit.weakVariants.length;
          if(varietyAudit.exactDuplicates.length)add('warning',`${title} — activités dupliquées`,varietyAudit.exactDuplicates.slice(0,3).map(r=>`${r.left}/${r.right}`).join(' · '),'Réécrire ou supprimer les copies exactes : un changement de type ou de raisonnement est préférable.',cpath);
          if(varietyAudit.nearDuplicates.length)add('warning',`${title} — formulations trop proches`,varietyAudit.nearDuplicates.slice(0,3).map(r=>`${r.left}/${r.right} (${Math.round(r.score*100)} %)`).join(' · '),'Varier la situation, le raisonnement demandé ou le format, pas seulement quelques mots.',cpath);
          if(varietyAudit.weakVariants.length)add('warning',`${title} — variantes de remédiation faibles`,varietyAudit.weakVariants.slice(0,3).map(r=>`${r.objective} · ${r.ids.join('/')}`).join(' · '),'Prévoir une activité liée mais réellement différente, idéalement avec un autre type d’interaction.',cpath);
        }
        if(acts.length>=6 && Object.keys(localTypes).length<3)add('warning',`${title} — variété limitée`,Object.entries(localTypes).map(([k,v])=>`${k}:${v}`).join(' · ')||'aucun type', 'Mixer au moins trois formats si le parcours est long : qcm, fill, matching, order.', cpath);
        if(acts.length>=6 && Object.keys(localPhases).length<2)add('warning',`${title} — progression peu visible`,Object.keys(localPhases).join(', ')||'aucune phase', 'Ajouter learning_phase pour distinguer compréhension, application, transfert ou remédiation.', cpath);
        if(backwardJumps)add('warning',`${title} — progression de difficulté instable`,`${backwardJumps} rupture(s) détectée(s)`, 'Réordonner ou qualifier les activités pour éviter les retours brusques expert → facile.', cpath);
      });
      if(totalActivities===0)add('warning','Aucune activité pédagogique détectée','Le kit ne peut pas être évalué côté apprentissage.', 'Corriger le contrat technique et ajouter activities[].', '$');
      const types=Object.keys(typeCounts).length;
      const objectives=Object.keys(objectiveCounts).length;
      const difficulties=Object.keys(difficultyCounts).length;
      const phases=Object.keys(phaseCounts).length;
      if(totalActivities && missingDifficulty/totalActivities>0.5)add('warning','Difficultés trop peu renseignées',`${totalActivities-missingDifficulty}/${totalActivities} activité(s) qualifiée(s)`, 'Ajouter difficulty progressivement : easy, medium, advanced, expert.', '$.courses[].activities[].difficulty');
      if(totalActivities && missingPhase/totalActivities>0.5)add('warning','Phases d’apprentissage trop peu renseignées',`${totalActivities-missingPhase}/${totalActivities} activité(s) qualifiée(s)`, 'Ajouter learning_phase pour piloter découverte, entraînement, transfert, remédiation.', '$.courses[].activities[].learning_phase');
      if(totalActivities && missingSuccess/totalActivities>0.35)add('warning','Feedback explicatif insuffisant',`${totalActivities-missingSuccess}/${totalActivities} activité(s) avec explication`, 'Ajouter why ou feedback.success pour expliquer pourquoi la réponse est correcte.', '$.courses[].activities[].why');
      if(totalActivities && missingRemediation/totalActivities>0.35)add('warning','Remédiation insuffisante',`${totalActivities-missingRemediation}/${totalActivities} activité(s) avec remédiation`, 'Ajouter remediation ou feedback.error pour transformer les erreurs en reprise utile.', '$.courses[].activities[].remediation');
      if(totalActivities>=8 && types<3)add('warning','Équilibre des formats faible',Object.entries(typeCounts).map(([k,v])=>`${k}:${v}`).join(' · '), 'Ajouter rappel actif ou manipulation : flashcard, fill, matching ou order.', '$');
      if(totalActivities && objectives<Math.min(3,totalActivities))add('warning','Couverture d’objectifs faible',`${objectives} objectif(s) distinct(s)`, 'Associer chaque activité à un objectif clair et regrouper les objectifs proches.', '$.courses[].activities[].objective');
      if(commonErrorsPresent===0 && totalActivities>=6)add('warning','Erreurs fréquentes absentes','Aucune common_errors détectée.', 'Ajouter common_errors sur les notions où les apprenants se trompent souvent.', '$.courses[].activities[].common_errors');
      if(assessmentRolePresent===0 && totalActivities>=8)add('warning','Rôle d’évaluation absent','Aucun assessment_role détecté.', 'Distinguer practice, diagnostic, validation et remediation pour rendre les évaluations interprétables.', '$.courses[].activities[].assessment_role');
      const applicationOrTransfer=Object.entries(phaseCounts).filter(([phase])=>['application','transfer','transfert'].includes(phase)).reduce((sum,[,count])=>sum+count,0);
      if(totalActivities>=6 && applicationOrTransfer===0)add('warning','Application ou transfert non démontré','Aucune activité n’est qualifiée application, transfer ou transfert.', 'Ajouter au moins une tâche qui demande d’utiliser la notion dans une situation différente du rappel initial.', '$.courses[].activities[].learning_phase');
      const ratios={
        objective: totalActivities?1-missingObjective/totalActivities:0,
        difficulty: totalActivities?1-missingDifficulty/totalActivities:0,
        phase: totalActivities?1-missingPhase/totalActivities:0,
        success: totalActivities?1-missingSuccess/totalActivities:0,
        remediation: totalActivities?1-missingRemediation/totalActivities:0,
        variety: Math.max(0,Math.min(1,types/3)-(nearDuplicateCount+exactDuplicateCount+weakVariantCount)/Math.max(1,totalActivities)*0.18),
        objectives: totalActivities?Math.min(1,objectives/Math.min(4,totalActivities)):0,
        mobile: totalActivities?Math.max(0,1-(longPrompt+longChoice)/(totalActivities*1.5)):0
      };
      const rawScore=Math.round(100*(0.18*ratios.objective+0.12*ratios.difficulty+0.12*ratios.phase+0.14*ratios.success+0.14*ratios.remediation+0.12*ratios.variety+0.12*ratios.objectives+0.06*ratios.mobile));
      const ceilings=[];
      const ceiling=(code,max,reason)=>ceilings.push({code,max,reason});
      if(totalActivities===0)ceiling('no-activities',0,'Aucune activité ne permet une séquence d’apprentissage.');
      if(totalActivities>0&&totalActivities<4)ceiling('mini-sequence-too-thin',54,'Moins de quatre activités ne suffisent pas à démontrer une mini-séquence complète.');
      if(totalActivities>=6&&types<3)ceiling('insufficient-interaction-variety',69,'Un parcours long avec moins de trois formats ne peut pas obtenir un grade A.');
      if(totalActivities>=6&&applicationOrTransfer===0)ceiling('no-application-or-transfer',69,'Le rappel seul ne démontre ni application ni transfert.');
      if(courseObjectivesMissing>0)ceiling('course-objectives-missing',79,'Des objectifs de parcours manquent.');
      if(totalActivities>=8&&assessmentRolePresent===0)ceiling('assessment-role-missing',79,'Aucune activité ne précise son rôle d’évaluation.');
      if(totalActivities>=6&&commonErrorsPresent===0)ceiling('error-model-missing',84,'Aucune erreur fréquente n’est modélisée.');
      if(exactDuplicateCount>0)ceiling('exact-duplicates-present',79,'Des activités strictement dupliquées affaiblissent la couverture réelle.');
      const effectiveCeiling=ceilings.length?Math.min(...ceilings.map(row=>row.max)):100;
      const score=Math.min(rawScore,effectiveCeiling);
      const grade=score>=85?'A':score>=70?'B':score>=55?'C':'D';
      const warnings=items.filter(i=>i.severity==='warning').length;
      const capText=effectiveCeiling<100?` · plafond ${effectiveCeiling} (${ceilings.map(row=>row.code).join(', ')})`:'';
      const summary=`Score pédagogique ${score}/100 · grade ${grade}${capText} · ${warnings} alerte(s)`;
      return {ok:true,schema:'learnit.pedagogical_quality.rc676.v2',score,rawScore,effectiveCeiling,ceilings,grade,items,warnings,recommendations:[...new Set(recommendations)].slice(0,12),stats:{source,courses:courses.length,totalActivities,typeCounts,difficultyCounts,phaseCounts,objectives,missingObjective,missingDifficulty,missingPhase,missingSuccess,missingRemediation,longPrompt,longChoice,commonErrorsPresent,assessmentRolePresent,applicationOrTransfer,nearDuplicateCount,exactDuplicateCount,weakVariantCount},ratios,summary};
    }

function buildPedagogicalQualityPanel(runtime,text=runtime.contentStore.importDraft){
      const d=buildPedagogicalQualityDiagnostics(runtime,text);
      const rows=(d.items||[]).slice(0,16).map(i=>`<div class="qa-item ${i.severity==='warning'?'warning':'info'}"><b>${i.severity==='warning'?'ALERTE':'INFO'}</b><span><strong>${escapeHtml(i.label)}</strong>${i.detail?`<br><span class="tiny">${escapeHtml(i.detail)}</span>`:''}${i.recommendation?`<br><span class="tiny">Conseil : ${escapeHtml(i.recommendation)}</span>`:''}</span></div>`).join('');
      const stats=d.stats||{}; const counts=stats.typeCounts||{};
      const typeBadges=Object.keys(counts).sort().map(k=>`<span class="badge">${escapeHtml(k)} · ${counts[k]}</span>`).join('')||'<span class="badge warn">Aucun type</span>';
      const score=d.score===null?'—':String(d.score);
      const grade=d.grade||'NA';
      return `<div class="contract-panel pedagogical-panel"><div class="contract-head"><div><h3>Qualité pédagogique du kit</h3><div class="contract-summary">${escapeHtml(d.summary)} · Plafonds de qualité explicites ; import technique indépendant.</div></div><span class="badge ${d.score!==null&&d.score>=70?'ok':'warn'}">${escapeHtml(grade)}</span></div><div class="import-preview-grid"><div class="import-stat"><b>${score}</b><span>score</span></div><div class="import-stat"><b>${stats.objectives||0}</b><span>objectifs</span></div><div class="import-stat"><b>${Object.keys(stats.phaseCounts||{}).length}</b><span>phases</span></div><div class="import-stat"><b>${stats.missingRemediation||0}</b><span>remédiations absentes</span></div></div><div class="import-type-row">${typeBadges}</div><div class="qa-list">${rows||'<p class="tiny">Aucune alerte pédagogique.</p>'}</div></div>`;
    }
