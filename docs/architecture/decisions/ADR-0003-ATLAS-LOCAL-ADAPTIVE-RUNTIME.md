# ADR-0003 — Atlas local adaptive runtime

- Status: Accepted
- Date: 2026-07-29
- Authority: issue #130 / `ATLAS-WP-001`
- Baseline: `06c06d5ea0cadcb3cb2084769ff5ada4d0fe0a35`

## Context

Learn-it doit devenir un système personnel d’apprentissage ambitieux tout en conservant les propriétés qui ont permis de promouvoir Learning Loop V2 : exécution locale, reprise fiable, artefact autonome, contrats testables et développement multi-IA contrôlé.

Le produit ne doit pas dépendre d’un LLM pendant l’utilisation. La prochaine action utile doit pourtant être calculée à partir des preuves observées et du temps disponible. La gamification doit soutenir l’apprentissage sans créer de récompense vide, de culpabilité ou de dépendance.

## Decision

1. Le runtime apprenant reste intégralement local et hors ligne.
2. Aucun LLM, appel API, secret ou service distant n’est utilisé pendant l’apprentissage.
3. M1 utilise un moteur adaptatif déterministe, embarqué et versionné.
4. Les faits d’apprentissage sont enregistrés comme événements immuables.
5. Les états visibles sont des projections recalculables.
6. Toute recommandation expose des codes de raison stables.
7. Entraînement, correction et validation restent sémantiquement distincts.
8. La gamification M1 valorise correction, autonomie, validation, reprise et transfert. Elle exclut monnaie virtuelle, classement public, récompense aléatoire et série punitive.
9. Quatre lanes IA travaillent en parallèle sur des chemins disjoints ; QA est indépendante et INT ne répare pas les fichiers de lane.
10. Un modèle statistique local futur n’est admissible que s’il bat une baseline déterministe sur des scénarios publiés, reste explicable, versionné, réversible et sans réseau.

## Consequences

### Positive

- produit utilisable sans compte ni connexion ;
- comportement reproductible et testable ;
- aucune donnée d’apprentissage envoyée à un fournisseur ;
- recommandations explicables ;
- architecture compatible avec une future synchronisation d’événements ;
- parallélisme de développement sans contrat implicite.

### Costs

- le planificateur initial sera moins flexible qu’un service génératif ;
- les règles de recommandation et leurs versions doivent être maintenues ;
- les événements et projections exigent des tests de compatibilité ;
- la gamification doit être validée par ses effets, pas par son apparence.

## Rejected alternatives

- LLM embarqué ou distant dans M1 ;
- backend obligatoire ;
- personnalisation opaque ;
- stockage d’un état unique écrasable sans journal ;
- gamification fondée sur points de clic, temps passé ou streak punitive ;
- réécriture complète de Learn-it Next.

## Rollback

La candidate Atlas peut être revertée sans migrer ni supprimer la baseline promue `06c06d5e…`. Les nouveaux événements Atlas doivent utiliser un espace de stockage isolé jusqu’à promotion.
