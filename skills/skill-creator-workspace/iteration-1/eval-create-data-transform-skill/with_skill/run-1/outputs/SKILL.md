---
name: csv-normalizer
description: Normalize CSV files by detecting column types, converting data types, handling null values, and exporting to Parquet format. Use when the user wants to clean, normalize, transform, or process CSV files — especially when they mention type detection, null handling, missing values, data cleaning, CSV-to-Parquet conversion, or preparing raw data for analysis. Trigger on any request involving CSV normalization, data pipeline ingestion, raw data cleaning, or batch file transformation, even without the word "normalize".
---

# CSV Normalizer

Nettoie et normalise des fichiers CSV : détection automatique des types, gestion des valeurs
nulles, conversion en Parquet. Conçu pour traiter des lots de fichiers bruts depuis une
source vers une destination propre.

---

## Contexte par défaut

- **Input** : `/data/raw/` (modifiable selon la requête)
- **Output** : `/data/clean/` (modifiable selon la requête)
- **Format cible** : Parquet (via pyarrow)
- **Stack** : Python 3.12+, pandas, pyarrow, chardet (optionnel pour l'encodage)

---

## Workflow

### 1. Découverte des fichiers

Lister tous les `.csv` dans le répertoire source. Si aucun fichier trouvé, informer
l'utilisateur et s'arrêter.

```bash
ls /data/raw/*.csv
```

### 2. Analyse par fichier

Pour chaque CSV, effectuer dans l'ordre :

**a. Détection de l'encodage**
Lire les premiers octets et détecter l'encodage. Priorité : UTF-8, puis Latin-1, puis chardet.

**b. Détection du séparateur**
Essayer dans l'ordre : `,` → `;` → `\t` → `|`. Utiliser `csv.Sniffer` ou compter les
occurrences sur les 5 premières lignes.

**c. Chargement**
```python
df = pd.read_csv(path, encoding=encoding, sep=separator)
```

**d. Inventaire des colonnes**
Afficher le schema détecté : nom, type pandas initial, nb de valeurs nulles, exemples
de valeurs (3 premières non-nulles).

### 3. Détection et conversion des types

Pour chaque colonne, appliquer la hiérarchie suivante (dans l'ordre) :

| Priorité | Type cible | Critères |
|----------|-----------|---------|
| 1 | `datetime` | Parseable par `pd.to_datetime` avec `infer_datetime_format=True` |
| 2 | `Int64` (nullable) | Tous les non-nulls sont des entiers |
| 3 | `Float64` (nullable) | Tous les non-nulls sont numériques |
| 4 | `boolean` | Valeurs in `{true, false, 1, 0, yes, no, oui, non}` (case-insensitive) |
| 5 | `string` | Fallback |

Utiliser les types nullable pandas (`Int64`, `Float64`, `boolean`) plutôt que numpy
pour préserver la distinction null/zéro.

### 4. Normalisation des valeurs nulles

Traiter comme nulles (→ `pd.NA`) les valeurs suivantes :
- Chaînes vides `""`
- `"NA"`, `"N/A"`, `"n/a"`, `"null"`, `"NULL"`, `"none"`, `"None"`, `"NaN"`, `"nan"`
- Espaces seuls `"   "`

Remplacer avant la détection de type. Cette étape est critique pour éviter les faux
positifs de typage (ex : une colonne avec "N/A" détectée comme string plutôt que float).

### 5. Export Parquet

```python
df.to_parquet(
    output_path,
    engine="pyarrow",
    compression="snappy",
    index=False
)
```

- Nom du fichier : même stem que le CSV source, extension `.parquet`
- Créer le répertoire de destination si inexistant

### 6. Rapport de normalisation

Après traitement de tous les fichiers, afficher un rapport structuré :

```
## Rapport de normalisation

### fichier.csv → fichier.parquet
| Colonne        | Type initial | Type final | Nulls avant | Nulls après |
|---------------|-------------|-----------|------------|------------|
| date_commande | object       | datetime   | 0           | 0           |
| montant       | object       | Float64    | 3           | 5           |
| ...           | ...          | ...        | ...         | ...         |

Lignes : 1 245 | Colonnes : 8 | Taille output : 42 KB

### Résumé global
- Fichiers traités : 3/3
- Erreurs : 0
- Colonnes converties : 18
- Valeurs null normalisées : 23
```

---

## Gestion des erreurs

**Fichier illisible** : logger l'erreur, passer au suivant (ne pas interrompre le batch).

**Colonne mixte (types mélangés)** : si la conversion échoue sur >5% des valeurs non-nulles,
garder le type `string` et noter dans le rapport avec les valeurs problématiques (max 5 exemples).

**Encodage inconnu** : tenter `errors="replace"` en dernier recours, noter dans le rapport.

**Répertoire de destination inexistant** : créer automatiquement avec `mkdir -p`.

---

## Exemple d'invocation

**Requête** : "Normalise les CSV dans /data/raw/, sort en Parquet dans /data/clean/"

**Actions** :
1. Scanner `/data/raw/*.csv`
2. Pour chaque fichier : détecter encodage + séparateur, charger, normaliser les nulls,
   convertir les types, exporter en Parquet
3. Afficher le rapport de normalisation

**Requête** : "Nettoie le fichier ventes.csv et convertis-le en Parquet"

**Actions** : même workflow sur le fichier unique spécifié.

---

## Dépendances Python

```
pandas>=2.0
pyarrow>=14.0
chardet>=5.0  # optionnel, pour détection d'encodage avancée
```

Vérifier avec `pip list` avant d'exécuter. Si manquant :
```bash
pip install pandas pyarrow chardet
```
