# Atlas M1 shared contracts

Version de bootstrap : `0.1`

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

```json
{
  "eventId": "uuid-v4",
  "eventVersion": 1,
  "occurredAt": "2026-07-29T09:00:00.000Z",
  "courseLineageId": "uuid-v4",
  "objectiveId": "uuid-v4",
  "activityLineageId": "uuid-v4",
  "kind": "activity-attempt",
  "assessmentRole": "practice",
  "outcome": "incorrect",
  "assistance": "none",
  "sessionId": "uuid-v4",
  "metadata": {}
}
```

Valeurs M1 minimales :

- `kind` : `activity-attempt`, `activity-corrected`, `session-started`, `session-interrupted`, `session-completed` ;
- `assessmentRole` : `practice`, `validation` ;
- `outcome` : `correct`, `incorrect`, `completed`, `interrupted` ;
- `assistance` : `none`, `hint`, `review`.

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

Invariants :

- `priority` est calculée par une règle embarquée versionnée ;
- `reasonCodes` explique la recommandation sans texte généré ;
- aucune recommandation ne dépend d’un réseau ou d’un LLM ;
- une activité non reliée à l’objectif est inéligible.

## `SessionPlan`

Plan déterministe pour une durée choisie.

```json
{
  "planVersion": 1,
  "sessionId": "uuid-v4",
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

Invariants :

- durées autorisées M1 : `5`, `15`, `30` ;
- même historique, même contenu, même horloge contrôlée et même version de moteur produisent le même plan ;
- le total estimé ne dépasse pas la durée choisie ;
- chaque item correspond à une recommandation admissible ;
- le plan reste sérialisable, exportable et reprenable.

## Ownership

- `ATLAS-CORE` produit et projette `LearningEvent`.
- `ATLAS-LEARNING` consomme `ObjectiveEvidence` et produit `LearningRecommendation` et `SessionPlan`.
- `ATLAS-EXPERIENCE` consomme les quatre contrats sans modifier leur sémantique.
- `ATLAS-CONTENT` garantit que les kits fournissent objectifs, activités et rôles nécessaires.
- INT compose les modules ; INT ne redéfinit aucun contrat.

Toute modification sémantique de ces quatre contrats exige un amendement explicite à `ATLAS-WP-001`.
