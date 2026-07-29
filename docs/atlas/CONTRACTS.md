# Atlas M1 shared contracts

Version de bootstrap : `0.2`

Ces contrats sont des interfaces de données. Ils ne définissent ni service distant, ni framework, ni format de stockage définitif.

## Principes

- objets sérialisables ;
- aucune fonction ou référence d’interface utilisateur ;
- identifiants canoniques existants ;
- timestamps explicites ;
- résultats déterministes pour les mêmes entrées ;
- aucune interprétation de titre, ordre ou nom de fichier comme identité.

## `LearningEvent`

Événement immuable décrivant un fait observé.

Exemple d’une tentative :

```json
{
  "eventId": "uuid-v4",
  "eventVersion": 1,
  "occurredAt": "2026-07-29T09:00:00.000Z",
  "kind": "activity-attempt",
  "sessionId": "uuid-v4",
  "courseLineageId": "uuid-v4",
  "objectiveId": "uuid-v4",
  "activityLineageId": "uuid-v4",
  "assessmentRole": "practice",
  "outcome": "incorrect",
  "assistance": "none",
  "metadata": {}
}
```

Valeurs M1 minimales :

- `kind` : `activity-attempt`, `activity-corrected`, `session-started`, `session-interrupted`, `session-completed` ;
- `assessmentRole` : `practice`, `validation` ;
- `outcome` : `correct`, `incorrect`, `completed`, `interrupted` ;
- `assistance` : `none`, `hint`, `review`.

Champs communs obligatoires pour tous les événements :

- `eventId` ;
- `eventVersion` ;
- `occurredAt` ;
- `kind` ;
- `sessionId` ;
- `metadata`.

Champs obligatoires selon `kind` :

- `activity-attempt` exige `courseLineageId`, `objectiveId`, `activityLineageId`, `assessmentRole`, `outcome` égal à `correct` ou `incorrect`, et `assistance` ;
- `activity-corrected` exige `courseLineageId`, `objectiveId`, `activityLineageId`, `assessmentRole` égal à `practice`, `outcome` égal à `completed`, et `assistance` égal à `review` ;
- `session-started` n’exige aucun identifiant de cours, d’objectif ou d’activité ;
- `session-interrupted` exige `outcome` égal à `interrupted` ; les identifiants de cours, d’objectif et d’activité sont facultatifs et ne sont présents que si l’interruption survient dans une activité ;
- `session-completed` exige `outcome` égal à `completed` et n’exige aucun identifiant de cours, d’objectif ou d’activité.

Un champ non applicable doit être absent. Il est interdit de créer un UUID fictif, une chaîne vide ou une valeur sentinelle pour satisfaire artificiellement la forme de l’événement.

Invariants :

- un événement publié n’est jamais modifié ;
- `eventId` est unique ;
- l’ordre logique repose sur `occurredAt`, puis `eventId` ;
- une correction n’est pas une validation ;
- une activité `practice` ne produit jamais de crédit `validation`.

## `ObjectiveEvidence`

Projection recalculable à partir des événements d’un objectif.

```json
{
  "objectiveId": "uuid-v4",
  "projectionVersion": 1,
  "practiceAttempts": 0,
  "latestPracticeCorrect": null,
  "needsReview": false,
  "correctionsCompleted": 0,
  "validationAttempts": 0,
  "latestValidationCorrect": null,
  "lastEvidenceAt": null,
  "state": "not-started",
  "reasons": []
}
```

États M1 :

- `not-started`
- `training`
- `review-needed`
- `ready-for-validation`
- `validated-recently`

Ces états décrivent le produit. Ils ne constituent pas une certification, une preuve de rétention durable ou une mesure officielle de maîtrise.

## `LearningRecommendation`

Recommandation locale et explicable.

```json
{
  "recommendationVersion": 1,
  "objectiveId": "uuid-v4",
  "action": "correct-practice",
  "priority": 100,
  "reasonCodes": ["RECENT_ERROR", "NO_INDEPENDENT_VALIDATION"],
  "estimatedMinutes": 5,
  "eligibleActivityIds": ["uuid-v4"]
}
```

Actions M1 :

- `start-practice`
- `continue-practice`
- `correct-practice`
- `attempt-validation`
- `maintain-recent-validation`

Registre canonique M1 de `reasonCodes` :

- `NEW_OBJECTIVE` : aucune preuve n’existe encore pour l’objectif ;
- `PRACTICE_IN_PROGRESS` : l’objectif possède un entraînement commencé mais incomplet ;
- `RECENT_ERROR` : une tentative récente est incorrecte ;
- `REVIEW_REQUIRED` : une correction est requise avant une nouvelle progression ;
- `CORRECTION_COMPLETED` : l’erreur a été corrigée sans constituer une validation ;
- `NO_INDEPENDENT_VALIDATION` : aucune validation distincte réussie n’est disponible ;
- `VALIDATION_AVAILABLE` : les préconditions locales d’une validation sont satisfaites ;
- `RECENTLY_VALIDATED` : une validation récente peut être entretenue sans affirmation de rétention durable ;
- `SESSION_TIME_LIMIT` : la durée choisie limite les actions admissibles dans la séance.

Toute addition, suppression ou modification sémantique d’un `reasonCode` exige un amendement explicite à `ATLAS-WP-001`.

Invariants :

- `priority` est calculée par une règle embarquée versionnée ;
- `reasonCodes` appartient au registre canonique M1 et explique la recommandation sans texte généré ;
- aucune recommandation ne dépend d’un réseau ou d’un LLM ;
- une activité non reliée à l’objectif est inéligible.

## `SessionPlan`

Plan déterministe pour une durée choisie.

```json
{
  "planVersion": 1,
  "planId": "sha256:normalized-input-and-plan-digest",
  "generatedAt": "2026-07-29T09:00:00.000Z",
  "durationMinutes": 15,
  "items": [
    {
      "position": 1,
      "objectiveId": "uuid-v4",
      "activityLineageId": "uuid-v4",
      "action": "correct-practice",
      "estimatedMinutes": 5,
      "reasonCodes": ["RECENT_ERROR"]
    }
  ],
  "unusedMinutes": 0
}
```

`planId` est dérivé de manière déterministe des entrées normalisées et de la version du moteur. Il identifie le plan, pas son exécution.

Lorsque l’utilisateur démarre réellement le plan, le runtime crée un `sessionId` UUID v4 distinct. Les événements de cette exécution portent ce `sessionId` et peuvent référencer `planId` dans `metadata`.

Invariants :

- durées autorisées M1 : `5`, `15`, `30` ;
- même historique, même contenu, même horloge contrôlée et même version de moteur produisent le même plan normalisé et le même `planId` ;
- l’identité aléatoire d’une exécution n’entre pas dans le calcul déterministe du plan ;
- le total estimé ne dépasse pas la durée choisie ;
- chaque item correspond à une recommandation admissible ;
- le plan reste sérialisable, exportable et reprenable.

## Ownership

- `ATLAS-CORE` produit les `LearningEvent` et calcule les projections `ObjectiveEvidence` ;
- `ATLAS-LEARNING` consomme `ObjectiveEvidence` et produit `LearningRecommendation` et `SessionPlan` ;
- `ATLAS-EXPERIENCE` consomme les quatre contrats sans modifier leur sémantique ;
- `ATLAS-CONTENT` garantit que les kits fournissent objectifs, activités et rôles nécessaires ;
- INT compose les modules ; INT ne redéfinit aucun contrat.

Toute modification sémantique de ces quatre contrats exige un amendement explicite à `ATLAS-WP-001`.
