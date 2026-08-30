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

M3.0 **Authoring Foundation** est le prochain incrément sélectionné en design seulement sous issue #223. Son vertical slice minimal est : kit canonique existant → édition visuelle → validation live → aperçu → export canonique déterministe → réimport sans dérive sémantique.

Le studio d’authoring reste une application locale/statique séparée du runtime apprenant. M3.0 n’autorise ni nouveau type d’activité, ni changement de contrat implicite, ni backend, ni compte, ni synchronisation, ni LLM runtime.

Les incréments ultérieurs de M3 couvriront séparément diagnostics pédagogiques, import de documents, assistance LLM hors runtime et passage à l’échelle/publication.

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

Baseline promue actuelle M2.2 :
- product HEAD accepté : `abaa0af0dcbd5338be2221587c1e871c4f939c52`
- QA HEAD accepté : `0e529f8b4f684a7c9aa900742efe94b2a012abc0`
- artefact : `366412` octets
- SHA-256 : `4b50af3dfe8820d258eaa73999b8a7e52b4991584d27986dca7e647af608f6d7`
- publication : `https://stefm78.github.io/learnit-platform/`

Prochain gate :
- issue `#223` — M3.0 Authoring Foundation design
- design uniquement ; aucune implémentation produit avant acceptation de ce gate.
