# Learn-it — Atlas M3.0 Authoring Foundation

M3.0 est un **studio auteur local et hors ligne**, séparé du runtime apprenant. Il permet d’ouvrir un kit Atlas canonique existant, de modifier ses champs visibles, d’obtenir la validation canonique en direct, de prévisualiser les activités QCM/fill et d’exporter un JSON déterministe ré-importable.

## Lancer le studio

Depuis la racine du dépôt :

```bash
python -m pip install -r apps/player/requirements-test.txt
python authoring/studio/server.py
```

Puis ouvrir `http://127.0.0.1:8765/`.

Le serveur refuse les adresses non loopback, n’active pas CORS et le code ne comporte aucun client réseau sortant. L’application Web n’utilise que des requêtes HTTP vers sa propre origine.

## Périmètre M3.0

Le studio travaille uniquement sur un **kit Atlas déjà valide**. Il permet de modifier :

- titre, description, version et langue du package ;
- titre, sous-titre et durée d’un parcours ;
- libellés des objectifs ;
- question, explication, difficulté, phase, rôle et durée des activités existantes ;
- libellés et bonne réponse d’un QCM existant ;
- textes, jetons, usages maximum et correspondances de réponses d’un `fill` existant.

M3.0 ne peut pas ajouter, supprimer ou réordonner un package, un parcours, un objectif, une activité, un choix, un emplacement ou un jeton. Les identifiants de lignée, identifiants de révision, digests et claims Atlas ne sont pas des champs auteur ordinaires.

## Identité, validation et export

Au premier changement sémantique d’une activité, le studio alloue une seule nouvelle révision UUIDv4 à cette activité, à son parcours et au package. Les modifications suivantes du même brouillon réutilisent ces révisions. Les lignées restent inchangées.

Au contrôle et à l’export, le cœur Python :

1. reconstruit les claims Atlas à partir des stimuli visibles ;
2. recalcule les digests activité → parcours → package ;
3. exécute le schéma gelé `learnit.kit.v2` ;
4. exécute le validateur général `authoring/v2/validate_kit.py` ;
5. exécute le validateur éditorial Atlas `authoring/v2/atlas/validate_atlas_content.py`.

Toute erreur bloquante interdit l’export. Un export modifié est sérialisé en UTF-8/NFC, clés triées et sans espaces insignifiants. Deux exports successifs du même brouillon sont identiques. Un import/export sans modification d’un kit canonique conserve exactement les octets source.

## Persistance

Le navigateur conserve uniquement le brouillon courant et sa provenance sous la clé locale :

```text
learnit.authoring.m3.v1
```

Le studio ne lit, ne migre, ne vide et n’écrit aucun stockage apprenant. **Abandonner le brouillon** supprime uniquement cette clé auteur.

## Aperçu

L’aperçu présente le contenu auteur QCM/fill et la bonne réponse pour relecture. Il est explicitement **non autoritatif** pour la recommandation Atlas, la mémoire, le transfert ou la maîtrise apprenant. La compatibilité runtime est prouvée par les validations et régressions Learn-it, pas par l’aperçu.
