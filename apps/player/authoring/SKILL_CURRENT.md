# SKILL — Générateur de kits Learn-it V13.3.0

## 0. Source de vérité

Ce skill cible **Learn-it RC718** et le contrat `learnit.import.v1.1`.

Lire dans cet ordre :

1. `contract/learnit-capabilities.json` ;
2. `contract/pedagogical-taxonomy.json` ;
3. `contract/learnit-import.schema.json`.

Ne générer par défaut que les capacités `stable` avec `generated_by_default: true`. Le schéma technique n’est pas recopié ici.

## 1. Sortie canonique

Produire un package `learnit-course-package` avec :

- `schema_version: learnit.import.v1.1` ;
- un `packageId` stable ;
- `source` ;
- `assets[]` ;
- `generation_report` ;
- `courses[]`.

Chaque parcours utilise `schemaVersion: learnit-content-v2`.

Découper un corpus très volumineux en plusieurs packages cohérents. Learn-it sait sélectionner plusieurs fichiers, les analyser ensemble et les importer dans une transaction unique.

## 2. Activités stables

- `qcm` : discriminer une notion ou un piège ; `answer` est l’index numérique correct.
- `fill` : reconstruire une formule ou une phrase courte.
- `matching` : associer deux ensembles.
- `order` : ordonner une méthode.
- `flashcard` : rappeler mentalement avant d’afficher la réponse.

Chaque activité contient au minimum `id`, `type`, `objective`, `question`, `why`, `remediation` et les champs propres à son type.

## 3. Métadonnées pédagogiques

Utiliser les valeurs exactes de `pedagogical-taxonomy.json` pour :

- `difficulty` ;
- `learning_phase` ;
- `assessment_role` ;
- `common_errors[]` ;
- `pedagogical_role` ;
- `transfer_distance` lorsqu’une activité est un probe de transfert.

Pour une vraie tâche de transfert, ajouter :

- `transfer_probe: true` ;
- `transfer_distance: near|far` ;
- `variant_of: <id>` pour relier la tâche à une activité source dont le contexte, les données ou le raisonnement ont été transformés.

Ne pas marquer `transfer_probe: true` sur une simple reformulation ou un exercice à nombres changés.

Les champs `skills` et `feedback` ne sont pas générés par défaut.

## 4. Images et médias

Déclarer les images dans `assets[]`, puis les référencer dans `media[]` par `assetId`.

- `alt` et `pedagogical_role` obligatoires ;
- formats stables : `svg`, `png`, `jpeg`, `webp`, `gif` ;
- SVG inline privilégié pour les schémas ;
- politique SVG **allowlist et fail-closed** : uniquement des formes, groupes, textes, définitions, dégradés, masques et chemins déclaratifs ;
- interdits dans un SVG : `script`, `foreignObject`, iframe, `image`, `use`, attribut `style`, attribut événementiel, lien `href`/`xlink:href`, URI externe et `url(...)` autre que `url(#identifiant-local)` ;
- pour une image raster embarquée : uniquement `data:image/png|jpeg|webp|gif;base64,...` ; les `data:image/svg+xml` sont refusées ;
- pour une image distante : URL HTTPS uniquement, sans identifiants intégrés ; HTTP, `javascript:`, `file:`, `blob:` et autres protocoles sont refusés ;
- les images distantes sont chargées sans référent HTTP ;
- une image principale par activité, sauf justification ;
- image utile ou absence d’image ;
- retirer les assets inutilisés.

## 5. Orchestration recommandée

1. activation : flashcard ou QCM simple ;
2. compréhension : QCM illustré ou matching ;
3. application : fill ou order ;
4. transfert : situation différente de l’exemple initial ;
5. consolidation : activité plus exigeante ;
6. validation : exercice court sans indice ;
7. remédiation : activité différente ciblant une erreur fréquente.

Éviter les distracteurs absurdes, le catalogue de définitions et les répétitions quasi identiques.

## 6. Couverture par objectif

Pour chaque objectif important :

- conserver exactement le même libellé `objective` sur les activités qui mesurent la même capacité ;
- prévoir au moins deux activités réellement différentes ;
- prévoir au moins une activité `assessment_role: validation` ;
- prévoir une activité ou variante `assessment_role: remediation` ou `learning_phase: remediation` ;
- prévoir une situation `learning_phase: transfer` dès que le parcours est suffisamment riche ;
- pour chaque objectif important, prévoir au moins un probe de transfert explicite ; préférer `transfer_distance: far` lorsque la situation change de contexte, de représentation ou de combinaison de concepts ;
- réserver `assessment_role: diagnostic` aux activités réellement utilisées pour situer un niveau et `assessment_role: validation` aux activités réellement utilisées pour confirmer un acquis ;
- utiliser `common_errors[]` pour relier les variantes qui ciblent le même piège.

Un kit techniquement valide mais sans validation, transfert ou remédiation peut être importable tout en recevant des avertissements pédagogiques.

## 6.1 Matrice de couverture RC698+

Avant livraison, établir pour chaque objectif une matrice explicite :

- rappel ou activation ;
- compréhension ;
- application ;
- transfert ;
- diagnostic ;
- validation ;
- remédiation.

La matrice ne doit pas produire un pourcentage opaque. Elle doit signaler les lacunes par codes lisibles, notamment `application-evidence-missing`, `transfer-evidence-missing`, `higher-order-assessment-missing` et `far-transfer-probe-missing`.

Une activité de validation n’est pas automatiquement une preuve de transfert. Une activité de transfert n’est pas automatiquement une validation. Les deux dimensions doivent être renseignées séparément.

## 7. Variété et anti-répétition

Le runtime peut espacer des activités proches, mais il ne doit pas compenser un kit mal conçu.

- changer la situation, le raisonnement demandé ou le type d’interaction ;
- ne pas fabriquer une variante en remplaçant seulement quelques mots ;
- éviter deux questions identiques ou deux QCM avec les mêmes distracteurs ;
- équilibrer rappel, compréhension, application, transfert, validation et remédiation ;
- prévoir au moins une variante réellement différente pour une erreur critique.

Ne jamais ajouter au kit de seed, ordre de séance, index d’affichage ou politique de mélange.

## 8. Remédiation ciblée

Pour chaque erreur critique :

- fournir une piste de méthode sans révéler toute la réponse ;
- utiliser une formulation ou un type d’activité différent de l’activité échouée ;
- garder l’activité compréhensible hors contexte ;
- ne jamais supposer une boucle infinie de remédiation.

## 9. Révision espacée et modes de séance

La planification, les modes, le feedback différé et la progression sont possédés par l’application.
Les preuves d’apprentissage, leurs agrégations et leurs statuts sont également calculés par le runtime à partir des interactions réelles.

Ne jamais ajouter dans les kits :

- date ou intervalle de révision ;
- niveau de mémoire ;
- compteur interne ;
- champ `mode` ;
- file de séance ;
- résultat ou statut apprenant ;
- recommandation calculée ;
- pourcentage de maîtrise.

Les cinq modes runtime sont Découverte, Entraînement, Révision, Validation et Diagnostic. Les flashcards sont exclues des modes d’évaluation.

## 10. Diagnostic du kit

Learn-it RC696 distingue trois niveaux :

- **blocage** : l’import est refusé ;
- **avertissement** : l’import reste possible, mais un risque technique ou pédagogique est explicité ;
- **conseil** : amélioration recommandée, non bloquante.

Chaque diagnostic possède un code stable, un chemin JSON, un impact et une correction proposée.

Avant livraison :

1. exécuter `python tools/validate_kit.py <fichier.json>` ;
2. corriger tous les blocages ;
3. traiter les avertissements pédagogiques prioritaires ;
4. vérifier les golden cases de `authoring/contract-fixtures.json` ;
5. exécuter `python dev/authoring_alignment.py` pour contrôler la chaîne capacité → schéma → validateur → runtime → golden kits ;
6. vérifier les deux parcours de référence `data/golden-kits/golden_nombres_complexes.json` et `data/golden-kits/golden_signaux_electriques.json` ;
7. vérifier qu’aucun asset n’est inutilisé et qu’aucune question n’est répétée à l’identique.

## 11. Prévisualisation et import

L’application possède le workflow d’import. Le kit ne doit contenir aucune instruction de collision ou de transaction.

Lors de l’import, l’utilisateur choisit une politique explicite :

- renommer automatiquement ;
- remplacer un parcours déjà importé ;
- ignorer le doublon ;
- bloquer l’import.

Les parcours natifs ne peuvent jamais être remplacés. L’application prévisualise sans écrire, puis applique tous les changements ou aucun. En cas d’échec, l’état précédent est restauré.

## 12. Procédure de livraison

1. Générer le ou les JSON.
2. Exécuter le validateur strict.
3. Corriger tous les blocages.
4. Relire les avertissements et conseils.
5. Vérifier la couverture objectifs × validation × remédiation × transfert.
6. Livrer uniquement les JSON importables et, si nécessaire, un bref rapport.

Aucun champ inconnu ou expérimental n’est ajouté sans évolution simultanée du manifeste, du schéma, du validateur, des tests, des golden kits et du skill.
