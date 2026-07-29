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

### M3 — Authoring Studio

Édition visuelle, aperçu, validation en direct, import de documents, assistance LLM hors runtime et publication de kits canoniques.

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

- issue : `#130`
- work package : `ATLAS-WP-001`
- baseline promue : `06c06d5ea0cadcb3cb2084769ff5ada4d0fe0a35`
- artefact promu SHA-256 : `9780bf3763864fbd42804a7dee129ae16e999e7971c4fce9a0a6a240d52b20df`
