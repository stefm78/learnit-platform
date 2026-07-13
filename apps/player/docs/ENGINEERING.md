# Contrats d’ingénierie RC715

## Propriétaires canoniques

- `next_action_model.js` : recommandation commune aux surfaces ;
- `session_mode_model.js` : files de session et pureté des rôles d’évaluation ;
- `learning_coverage_model.js` : couverture explicite rappel/compréhension/application/transfert ;
- `retention_protocol_model.js` : observations immédiate, 72 h et 7 jours ;
- `65_mobile_swipe_runtime.js` : moteur du carrousel ;
- `69_gesture_orchestrator.js` : orchestrateur tactile ;
- `74_learning_evidence_runtime.js` : pont runtime pour couverture et rétention.

Les redéfinitions historiques restantes sont des décorateurs enregistrés dans `OWNER_MAP.json`. Une nouvelle redéfinition non enregistrée fait échouer le gate d’architecture.

## Contrats pédagogiques

- aucun pourcentage opaque ne remplace la matrice de couverture ;
- Diagnostic et Validation utilisent leurs rôles stricts lorsqu’ils existent ;
- toute probe de transfert indique `transfer_probe`, `transfer_distance` et `variant_of` ;
- un transfert lointain de validation est attendu par objectif dans les golden probes ;
- la rétention n’est jamais déclarée avant les observations prévues.

## Dette et CSS

- les modèles sans consommateur sont retirés, pas archivés dans la source active ;
- les namespaces `rcXXX` historiques sont recensés comme dette de compatibilité et aucun nouveau nom de fichier actif ne porte un numéro de RC ;
- les doublons exacts et déclarations masquées d’un même sélecteur sont interdits ;
- le nettoyage reste ciblé, sans réécriture globale.

## Release

- build déterministe ;
- artefact testé identique à l’artefact packagé ;
- preuves liées aux SHA exacts du test, du manifeste, du registre et de l’artefact ;
- test clean-room octet pour octet ;
- `promotionReady` reste faux jusqu’aux gates humains RC702 et RC713.


## Persistance Bibliothèque RC713+

IndexedDB est le propriétaire durable des parcours importés. `localStorage` reste un cache synchrone de démarrage. L’identité d’un parcours importé est `localCourseId`, immuable après import ; le titre est une propriété de présentation modifiable.
