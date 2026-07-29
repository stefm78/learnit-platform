# Atlas M1 — contenu canonique

Cette lane fournit deux packages statiques `learnit.kit.v2` et un validateur éditorial déterministe. Elle n’ajoute aucune logique produit runtime, aucun appel réseau et aucun LLM.

## Livrables

- `nombres_complexes_atlas.json`
- `signaux_electriques_atlas.json`
- `validate_atlas_content.py`
- test de lane : `apps/learnit-next/tests/atlas_m1_content.py`

Chaque package contient trois profils de séance, ordonnés et explicitement estimés à **5, 15 et 30 minutes**. Chaque profil expose un objectif canonique et cinq activités.

## Sources pédagogiques

### Nombres complexes

Le kit s’appuie sur *MI2 — Nombres Complexes*, seconde édition du 17 février 2026 :

- forme algébrique, parties réelle et imaginaire ;
- calculs, conjugué, inverse et quotient ;
- plan complexe, module et argument ;
- formes trigonométrique et exponentielle ;
- racines et transfert vers une situation non isomorphe.

### Signaux électriques

Le kit s’appuie sur *Des signaux pour communiquer*, cours de physique S2 EPF FGE1, version du 11 janvier 2026 :

- loi d’Ohm, puissance et conventions ;
- lois de Kirchhoff ;
- associations de résistors et diviseur de tension ;
- modèles de Thévenin et de Norton ;
- mise en charge et diagnostic qualitatif d’une source réelle.

## Profil éditorial Atlas sans changement de schéma

Le schéma gelé ne possède ni champ `correction` ni durée par activité. La lane n’ajoute aucun champ. Elle exprime la boucle Atlas uniquement avec les champs existants :

| Preuve pédagogique | Représentation `learnit.kit.v2` |
|---|---|
| entraînement | `assessmentRole: "practice"` avec phase `activation`, `comprehension` ou `application` |
| possibilité d’erreur | activité d’application avec distracteurs contrôlés |
| correction | activité distincte `learningPhase: "consolidation"` et `assessmentRole: "practice"` |
| validation indépendante | activité distincte `learningPhase: "validation"` et `assessmentRole: "validation"` |
| transfert | activité ultérieure `learningPhase: "transfer"` et `assessmentRole: "practice"` |
| durée 5/15/30 | `course.estimatedMinutes` égal à `5`, `15` ou `30` |

Pour chaque objectif, le validateur exige l’ordre :

`entraînement ≤ possibilité d’erreur < correction < validation < transfert`

L’égalité entre entraînement et possibilité d’erreur signifie qu’une même activité d’application constitue l’entraînement au cours duquel une erreur observable peut se produire. La correction et la validation restent toujours des activités distinctes.

## Identités et révisions

Les identifiants de lignée de package, cours, objectif et activité sont gelés dans le validateur. Une évolution de contenu conserve ces identifiants de lignée, alloue de nouveaux identifiants de révision et recalcule les digests SHA-256 canoniques.

Le validateur rejette notamment :

- dérive d’identifiant canonique ou d’ordre ;
- identifiant dupliqué ou référence d’objectif absente ;
- activité de validation confondue avec l’entraînement ;
- correction, validation ou transfert manquant ;
- validation placée avant la correction ;
- QCM ambigu ou réponse correcte non déclarée ;
- fill incomplet, ambigu ou incohérent avec `maxUses` ;
- champ hors `learnit.kit.v2` ;
- digest de révision périmé ;
- placeholder éditorial ou URL distante.

## Commandes

Depuis la racine du dépôt :

```bash
python authoring/v2/atlas/validate_atlas_content.py
python authoring/v2/atlas/validate_atlas_content.py --format json
python apps/learnit-next/tests/atlas_m1_content.py
```

Le validateur réutilise le validateur canonique v2 du dépôt puis applique les invariants éditoriaux Atlas.
