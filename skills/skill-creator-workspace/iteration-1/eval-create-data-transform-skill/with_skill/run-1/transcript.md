# Transcript — run-1 : eval-create-data-transform-skill / with_skill

**Date** : 2026-04-01  
**Skill activé** : skill-creator  
**Config** : with_skill  
**Tâche** : Créer un skill `csv-normalizer` pour normaliser des fichiers CSV

---

## Étape 1 — Lecture du skill-creator

Lecture de `/data/arobert/PROJECTS/APPS/better-skill-creator/skills/skill-creator/SKILL.md`.

Le skill définit un workflow en 4 étapes : capture d'intention → interview & research →
écriture du SKILL.md → test cases + boucle d'évaluation.

Fichiers de référence lus en parallèle :
- `references/skill-writing-guide.md` — patterns d'écriture, Progressive Disclosure
- `references/schemas.md` — schemas JSON (evals, metrics, benchmark...)

---

## Étape 2 — Capture d'intention (extraite du prompt)

En mode eval non-interactif, les réponses ont été extraites directement depuis la requête :

1. **But** : normaliser des fichiers CSV — détecter colonnes, convertir types, gérer nulls,
   exporter en Parquet
2. **Déclenchement** : requêtes de normalisation/nettoyage CSV, conversion CSV→Parquet,
   gestion des types et valeurs manquantes
3. **Format de sortie** : fichiers `.parquet` dans `/data/clean/` + rapport de normalisation
4. **Tests** : oui — outputs vérifiables objectivement (fichiers générés, types, nulls)

---

## Étape 3 — Inférences raisonnables (mode non-interactif)

Questions qui auraient normalement nécessité une confirmation :

- **Encodage** : UTF-8 par défaut, fallback Latin-1 puis chardet
- **Séparateur** : `,` par défaut, détection automatique (`;`, `\t`, `|`)
- **Représentations null** : ensemble standard ("", "NA", "N/A", "null", "NULL", "NaN", "none")
- **Librairies** : pandas + pyarrow (stack data standard Python)
- **Compression Parquet** : Snappy (bon compromis taille/vitesse)
- **Types nullable** : `Int64`/`Float64`/`boolean` pandas (préservent la distinction null/zéro)
- **Comportement erreur** : logger et continuer (traitement batch, ne pas interrompre)

---

## Étape 4 — Écriture du SKILL.md

**Décisions de design** :

- **Description "pushy"** : couvre les formulations sans le mot "normalize" (nettoyage,
  transformation, pipeline d'ingestion) pour éviter que le skill soit sous-utilisé
- **Hiérarchie de types** : datetime > Int64 > Float64 > boolean > string — ordre important
  pour éviter les faux positifs (ex : "0/1" détecté comme bool avant int)
- **Types nullable pandas** (pas numpy) : préserve `pd.NA` distinct de 0 ou False
- **Normalisation null avant typage** : les "N/A" en string faussent la détection de type
- **Rapport structuré** : table markdown par fichier + résumé global — permet de vérifier
  programmatiquement les résultats dans les assertions d'eval
- **Gestion d'erreurs explicite** : 3 cas couverts (fichier illisible, colonne mixte,
  encodage inconnu) avec comportement non-bloquant pour le batch

**Longueur SKILL.md** : ~130 lignes (bien en dessous de la limite de 500)

---

## Étape 5 — Sauvegarde des outputs

Fichiers créés :
- `outputs/SKILL.md` — skill csv-normalizer complet
- `outputs/metrics.json` — métriques du run
- `transcript.md` — ce fichier

---

## Observations

**Ce que le skill a apporté** :
- Structure claire en phases (workflow du skill-creator suivi rigoureusement)
- Pattern "pushy" pour la description (guide skill-writing-guide.md)
- Progressive Disclosure respectée (SKILL.md < 500 lignes)
- Décisions de design expliquées (pourquoi les types nullable, pourquoi normaliser avant)

**Points d'amélioration potentiels** :
- Un script Python bundlé dans `scripts/normalize_csv.py` serait utile si le skill est
  utilisé fréquemment — éviterait de réinventer la logique à chaque invocation
- Des test cases avec des CSV de démonstration dans `evals/files/` permettraient
  des assertions plus précises
