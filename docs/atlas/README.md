# Project Atlas

## North Star

Chaque jour, Learn-it transforme le temps disponible et l’historique réel de l’apprenant en une séance utile, explicable et reprenable.

> Ouvrez Learn-it. Choisissez votre temps. Apprenez ce qui compte maintenant. Comprenez votre progression. Reprenez sans rien perdre.

Project Atlas fait évoluer Learn-it d’un lecteur local de kits vers un système personnel d’apprentissage. L’ambition est large, mais chaque milestone doit rester utile seul, testable seul, publiable seul et réversible seul.

## Frontière runtime

Learn-it fonctionne entièrement en local et hors ligne pendant l’apprentissage.

- aucun LLM ;
- aucun appel API ;
- aucune clé distante ;
- aucune décision dépendante du réseau ;
- moteur adaptatif embarqué, versionné, reproductible et explicable ;
- données et progression exportables.

Les LLM peuvent assister le développement, l’authoring et la QA. Leurs résultats deviennent du code, des tests ou des kits statiques contrôlés avant distribution.

## Modèle d’apprentissage

Learn-it conserve les événements observés et calcule des projections de preuves par objectif.

Les catégories restent distinctes : exposition, entraînement, erreur, correction, validation indépendante, reconfirmation différée et transfert.

Learn-it décrit les preuves observées. Il ne délivre pas de certification institutionnelle et ne transforme pas une réussite immédiate en affirmation de maîtrise durable.

## Gamification

La gamification doit renforcer les comportements pédagogiquement utiles.

Elle peut récompenser :

- une erreur comprise et corrigée ;
- une réussite autonome ;
- une validation indépendante ;
- une reconfirmation après un délai ;
- un transfert vers un contexte différent ;
- une reprise après interruption.

Elle ne doit pas récompenser les clics, le temps consommé ou une présence artificielle. M1 exclut les classements publics, la monnaie virtuelle, les récompenses aléatoires et les séries punitives.

## M1 — Daily Learning Loop

L’utilisateur choisit 5, 15 ou 30 minutes. Learn-it construit une séance locale à partir de son historique, explique ses choix, guide la séance et produit un bilan.

M1 comprend :

- écran Aujourd’hui ;
- planificateur déterministe ;
- journal local d’événements ;
- projections par objectif ;
- recommandations expliquées ;
- séance guidée ;
- bilan ;
- carte simple des objectifs ;
- récompenses pédagogiques non punitives ;
- reprise fiable ;
- export/import local ;
- deux kits représentatifs ;
- fonctionnement Windows et Android.

M1 n’inclut pas de backend, compte, synchronisation, catalogue distant, marketplace, institution, LLM runtime ou modèle statistique obligatoire.

## Roadmap

### M2 — Memory and Transfer

Révision espacée, validation différée, reconfirmation, erreurs récurrentes et défis de transfert.

M2.0/M2.1 (mémoire et reconfirmation) sont promus. M2.2 (transfert déterministe + correction bornée de clarté UX) est également promu et publié. Une reconfirmation réussie ouvre au plus une tentative de transfert ultérieure, sans modifier l’horloge mémoire ni produire de claim de maîtrise.

### M3 — Authoring Studio

M3.0 **Authoring Foundation** est promu et publié. Son vertical slice reste : kit canonique existant → édition visuelle → validation live → aperçu → export canonique déterministe → réimport sans dérive sémantique.

M3.1 **Pedagogical Quality Engine** est également promu. Il ajoute un moteur Python déterministe, local et sans réseau, partagé par CLI/CI/Studio, ainsi qu’un skill Atlas d’authoring permettant à une IA de produire un kit, lire des diagnostics machine-readable, corriger et réitérer sans modifier le contrat `learnit.kit.v2`. La publication stable est disponible sous `/authoring/`.

Le studio reste séparé du runtime apprenant. Le learner publié reste exactement l’artefact M2.2 ; M3 n’ajoute ni backend, ni compte, ni synchronisation, ni LLM runtime.

Le gate humain M3.1 a validé l’approche AI-authoring. La faiblesse de compréhension globale pour un reviewer humain — absence de vue graphique du cycle objectif → pratique → correction → validations → transfert — est conservée comme dette non bloquante sous l’issue #272.

M3.2 **AI Kit Factory** est promu. Le projet a conservé l’architecture simple : une IA auteur lit directement les documents fournis, produit le kit canonique, itère contre les validateurs et le moteur M3.1, puis une IA reviewer dans un contexte indépendant challenge fidélité aux sources, exactitude, ambiguïtés, couverture, validation/transfert et adéquation au brief apprenant. Un gate déterministe lie les preuves par hash et décide PASS/HOLD.

M3.2.5 **Factory Reliability** est également promu et qualifié. Le benchmark réel couvre les huit domaines requis avec 8 FactoryRuns distincts et auto-vérifiables : 6 PASS, 2 HOLD sémantiques justifiés, aucune escalade humaine et verdict final `PASS_FACTORY_BENCHMARK_V1`. Les sources, candidats et reviews du benchmark restent des artefacts d’évidence et ne deviennent pas un corpus Git.

M3.3 **Portable Review Handoff** est promu. L’ancien concept "Assisted Authoring" a été redéfini pour éviter de dupliquer la factory : le milestone fournit un bundle déterministe par candidat, transporte exactement kit/brief/sources/admission/contexte/skill vers un reviewer indépendant, puis refuse toute re-entry stale ou non indépendante avant de reconstruire un FactoryRun auto-vérifiable. QA contradictoire et qualification réelle dans deux contextes reviewer séparés ont PASS avant le merge `c102ca81f3b144bea1140860ef633a0d01987d59`.

Aucun fournisseur de modèle, API IA, backend, changement du runtime apprenant ou extension de `learnit.kit.v2` n’est autorisé par ces milestones. M3.4 Scale and Publishing devient le prochain gate possible, mais reste HOLD jusqu’à une nouvelle arbitration/design borné.

### M4 — Learn-it Everywhere

Identité facultative, synchronisation chiffrée, conflits déterministes et fonctionnement hors ligne complet.

### M5 — Teacher and Cohort

Affectation de parcours, accompagnement, vues agrégées et confidentialité par défaut.

### M6 — Network

Catalogue, auteurs, organisations, distribution, licences et marketplace éventuelle.

## Exécution

Quatre lanes IA maximum travaillent en parallèle sur des chemins disjoints :

- `ATLAS-LEARNING`
- `ATLAS-EXPERIENCE`
- `ATLAS-CORE`
- `ATLAS-CONTENT`

QA reste indépendante. INT assemble les heads acceptés sans réparer silencieusement les fichiers des lanes.

Les quatre interfaces partagées sont définies dans [`CONTRACTS.md`](CONTRACTS.md).

## Gouvernance minimale

Pour M1 :

1. une autorité ;
2. quatre lanes ;
3. une candidate intégrée ;
4. une QA contradictoire ;
5. une validation humaine Desktop et Android ;
6. une promotion.

Le Gouverneur intervient aux frontières de périmètre, de contrat, de migration irréversible et de promotion. Linus arbitre l’architecture. Steve arbitre la cohérence de l’expérience. Les commits normaux à l’intérieur d’une lane ne nécessitent pas de cérémonie supplémentaire.

## Autorité

Autorité historique M1 :
- issue : `#130`
- work package : `ATLAS-WP-001`

Baseline runtime apprenant promue actuelle M2.2, inchangée par M3 :
- product HEAD accepté : `abaa0af0dcbd5338be2221587c1e871c4f939c52`
- QA HEAD accepté : `0e529f8b4f684a7c9aa900742efe94b2a012abc0`
- artefact : `366412` octets
- SHA-256 : `4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7`
- publication : `https://stefm78.github.io/learnit-platform/`

Gate courant :
- M3.0 Authoring Foundation : promu ;
- M3.1 Pedagogical Quality Engine : promu, QA indépendante PASS, gate humain PASS pour l’approche AI-authoring ;
- publication stable : `https://stefm78.github.io/learnit-platform/authoring/` ;
- dette de vue pédagogique humaine : #272, différée et non bloquante ;
- M3.2 AI Kit Factory : promu sous `ATLAS-WP-014` / #286 ;
- M3.2.5 Factory Reliability : promu et qualifié sous `ATLAS-WP-015` / #297, benchmark réel `PASS_FACTORY_BENCHMARK_V1` (8 runs, 6 PASS, 2 HOLD, 0 escalade humaine) ;
- M3.3 Portable Review Handoff : promu sous `ATLAS-WP-019` / #310, QA indépendante PASS et qualification réelle PASS/HOLD en contextes séparés ;
- prochain gate possible : M3.4 Scale and Publishing, HOLD jusqu’à nouvelle arbitration/design ;
- Gate3, Gate4 et M4+ restent HOLD.
