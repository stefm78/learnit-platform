# Learn-it — source minimale RC715

RC715 est une **candidate automatisée en HOLD humain** construite sur RC712.

RC713–RC715 ajoutent :

- une bibliothèque importée persistée dans IndexedDB, avec `localStorage` comme cache synchrone ;
- une restauration automatique après fermeture/réouverture lorsque le cache local est indisponible ou éphémère ;
- un nom de parcours modifiable pendant la prévisualisation d’import ;
- un renommage post-import depuis la fiche Bibliothèque ;
- un identifiant local stable, afin qu’un renommage ne perde ni progression, ni bilan, ni reprise ;
- des tests navigateur dédiés à la persistance et au renommage.

## Commandes reproductibles

```bash
python dev/update_manifest.py
python build.py
python dev/run_all_checks.py --skip-build --include-browser --artifact dist/learnit.html
python dev/release_pipeline.py --output-dir release
```

## Statut

- `automationReady: true` seulement après tous les gates automatisés ;
- `promotionReady: false` jusqu’au test humain RC716 ;
- RC702 transfert/rétention est explicitement différée ;
- RC716 : fermeture/réouverture, renommage à l’import et après import, plus matrice finale.
