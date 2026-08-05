# Contenus Atlas M1 — contrat 0.3

Deux kits représentatifs et scientifiquement bornés sont fournis : nombres complexes et signaux électriques.

Chaque objectif conserve, dans l’ordre exact de `course.activities`, cinq classes :

1. entraînement : `application + practice` ;
2. correction : `consolidation + practice` ;
3. validation autonome initiale : `validation + validation` ;
4. validation distincte de maintenance : `validation + validation` ;
5. transfert : `transfer + practice`, classifié mais jamais planifié par Atlas M1.

`estimatedMinutes` est déclaré par activité. Les profils 5, 15 et 30 minutes sont des budgets du planificateur : le validateur prouve qu’une activité préférée de chaque boucle tient dans 5 minutes, sans prétendre qu’une boucle de cinq activités entière tient dans ce budget.

Les claims d’indépendance sont relationnels au niveau du cours. Ils relient exactement objectif, activité source et activité cible, avec digests `atlas.stimulus.v1`. Un digest distinct est nécessaire mais ne vaut pas acceptation QA.

Sources :
- *MI2 — Nombres Complexes*, EPF Mathématiques S2, 2e édition, 17 février 2026 ;
- *Des signaux pour communiquer*, EPF FGE1 S2, version du 11 janvier 2026.
