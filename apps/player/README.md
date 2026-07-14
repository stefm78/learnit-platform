# Learn-it — source minimale RC718

RC718 est une **candidate automatisée** construite sur la baseline standalone RC715 promue et validée humainement.

RC716–RC718 ajoutent, sans modifier l’identité technique des packages :

- le renommage du plan importé depuis la Bibliothèque ;
- le choix du nom du plan pendant la prévisualisation d’import ;
- une persistance durable du nom dans IndexedDB et le cache local ;
- la conservation des identifiants de parcours, de la progression, du bilan et de la reprise ;
- le rejet des noms vides, trop longs ou déjà utilisés ;
- des contrôles contractuels et navigateur dédiés.

## Commandes reproductibles

```bash
python dev/update_manifest.py
python build.py
python dev/run_all_checks.py --skip-build --include-browser --artifact dist/learnit.html
python dev/release_pipeline.py --output-dir release
```

## Statut

- baseline promue : RC715 ;
- candidate courante : RC718 ;
- automatisation : en validation complète ;
- prochain gate humain ciblé : RC719, renommage du plan sur Android et desktop avec fermeture/réouverture.
