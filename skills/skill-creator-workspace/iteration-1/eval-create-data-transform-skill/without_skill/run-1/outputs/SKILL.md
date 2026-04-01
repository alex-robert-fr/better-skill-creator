---
name: csv-normalizer
description: Normalise des fichiers CSV bruts en détectant automatiquement les colonnes, convertissant les types, gérant les valeurs nulles et exportant en format Parquet. Traite les fichiers depuis /data/raw/ et exporte les résultats dans /data/clean/.
---

# CSV Normalizer

Tu es un expert en traitement de données. Ton rôle est de normaliser des fichiers CSV depuis `/data/raw/` et d'exporter les résultats en Parquet dans `/data/clean/`.

## Processus de normalisation

### Étape 1 — Découverte et analyse des fichiers

1. Lister tous les fichiers `.csv` dans `/data/raw/`
2. Pour chaque fichier, effectuer une analyse préliminaire :
   - Lire les 5 premières lignes pour détecter le séparateur (`,`, `;`, `\t`, `|`)
   - Identifier les noms de colonnes (première ligne ou auto-généré si absent)
   - Estimer le nombre de lignes

### Étape 2 — Détection des colonnes et des types

Pour chaque colonne, détecter le type dominant en analysant un échantillon représentatif :

| Type cible | Critères de détection |
|------------|----------------------|
| `integer`  | Valeurs entières uniquement (après nettoyage des espaces) |
| `float`    | Valeurs numériques avec décimales |
| `boolean`  | Valeurs `true/false`, `yes/no`, `1/0`, `oui/non` (insensible à la casse) |
| `datetime` | Formats ISO 8601, `DD/MM/YYYY`, `YYYY-MM-DD`, timestamps Unix |
| `date`     | Formats date sans composante horaire |
| `string`   | Tout le reste |

**Règles de priorité :**
- Si >80% des valeurs non-nulles correspondent à un type, adopter ce type
- En cas d'ambiguïté entre `integer` et `float`, choisir `float`
- Les colonnes avec >50% de valeurs nulles restent en `string` sauf si les valeurs présentes sont clairement typées

### Étape 3 — Gestion des valeurs nulles

Identifier les représentations de valeurs nulles :
- Cellules vides
- Chaînes : `"null"`, `"NULL"`, `"NA"`, `"N/A"`, `"na"`, `"n/a"`, `"none"`, `"NONE"`, `"-"`, `"?"`
- Valeurs numériques sentinelles communes : `-999`, `-9999`, `99999` (à confirmer avec le contexte)

**Stratégie par type :**
- `integer` / `float` : remplacer par `NaN` (Pandas) ou `null` (Parquet nullable)
- `string` : remplacer par `None` / valeur nulle Parquet
- `datetime` / `date` : remplacer par `NaT`
- `boolean` : remplacer par `None`

### Étape 4 — Nettoyage et normalisation

- Supprimer les espaces en début/fin de chaque valeur string
- Normaliser les noms de colonnes : minuscules, espaces → underscores, supprimer les caractères spéciaux
- Déduplication : signaler (sans supprimer) les lignes dupliquées exactes
- Lignes entièrement nulles : supprimer

### Étape 5 — Export en Parquet

Exporter chaque CSV normalisé en Parquet dans `/data/clean/` :
- Nom du fichier : même nom de base, extension `.parquet` (ex: `sales_2024.csv` → `sales_2024.parquet`)
- Compression : `snappy` (équilibre taille/vitesse)
- Schéma : inclure les métadonnées de types dans le fichier Parquet

## Script Python de référence

```python
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
import re

RAW_DIR = Path("/data/raw")
CLEAN_DIR = Path("/data/clean")
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

NULL_REPRESENTATIONS = {
    "null", "NULL", "NA", "N/A", "na", "n/a",
    "none", "NONE", "-", "?", ""
}

def normalize_column_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name

def detect_separator(filepath: Path) -> str:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        first_line = f.readline()
    for sep in [",", ";", "\t", "|"]:
        if sep in first_line:
            return sep
    return ","

def replace_nulls(series: pd.Series) -> pd.Series:
    return series.replace(list(NULL_REPRESENTATIONS), pd.NA)

def infer_and_cast(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        series = replace_nulls(df[col].astype(str))
        non_null = series.dropna()

        if non_null.empty:
            continue

        # Tentative boolean
        bool_map = {
            "true": True, "false": False,
            "yes": True, "no": False,
            "oui": True, "non": False,
            "1": True, "0": False
        }
        bool_values = non_null.str.lower()
        if bool_values.isin(bool_map.keys()).mean() > 0.8:
            df[col] = series.str.lower().map(bool_map).astype(pd.BooleanDtype())
            continue

        # Tentative datetime
        try:
            parsed = pd.to_datetime(non_null, infer_datetime_format=True, errors="coerce")
            if parsed.notna().mean() > 0.8:
                df[col] = pd.to_datetime(series, infer_datetime_format=True, errors="coerce")
                continue
        except Exception:
            pass

        # Tentative numérique
        numeric = pd.to_numeric(non_null.str.replace(",", ".", regex=False), errors="coerce")
        if numeric.notna().mean() > 0.8:
            is_integer = (numeric.dropna() % 1 == 0).all()
            num_series = pd.to_numeric(
                series.str.replace(",", ".", regex=False), errors="coerce"
            )
            df[col] = num_series.astype(pd.Int64Dtype() if is_integer else float)
            continue

        # Fallback string
        df[col] = series.where(series.notna(), other=pd.NA).astype(pd.StringDtype())

    return df

def process_file(csv_path: Path) -> dict:
    sep = detect_separator(csv_path)
    df = pd.read_csv(csv_path, sep=sep, dtype=str, keep_default_na=False)

    # Normaliser les noms de colonnes
    df.columns = [normalize_column_name(c) for c in df.columns]

    # Supprimer les lignes entièrement nulles
    original_len = len(df)
    df = df.replace(list(NULL_REPRESENTATIONS), pd.NA)
    df = df.dropna(how="all")

    # Détecter les doublons
    n_duplicates = df.duplicated().sum()

    # Inférer et caster les types
    df = infer_and_cast(df)

    # Exporter en Parquet
    out_path = CLEAN_DIR / (csv_path.stem + ".parquet")
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, out_path, compression="snappy")

    return {
        "file": csv_path.name,
        "rows_input": original_len,
        "rows_output": len(df),
        "rows_dropped": original_len - len(df),
        "duplicates_detected": int(n_duplicates),
        "columns": {col: str(df[col].dtype) for col in df.columns},
        "output": str(out_path)
    }

# Traitement principal
results = []
for csv_file in sorted(RAW_DIR.glob("*.csv")):
    print(f"Traitement : {csv_file.name}")
    result = process_file(csv_file)
    results.append(result)
    print(f"  ✓ {result['rows_output']} lignes exportées → {result['output']}")
    if result["duplicates_detected"] > 0:
        print(f"  ⚠ {result['duplicates_detected']} lignes dupliquées détectées")

print(f"\nTraitement terminé : {len(results)} fichier(s) normalisé(s).")
```

## Rapport de sortie

Après traitement, générer un rapport récapitulatif :

```
=== Rapport de normalisation CSV → Parquet ===

Fichiers traités : N
Répertoire source : /data/raw/
Répertoire cible  : /data/clean/

┌─────────────────┬────────┬────────┬─────────┬────────────────────────────────┐
│ Fichier         │ Lignes │ Sortie │ Supprim │ Colonnes détectées             │
├─────────────────┼────────┼────────┼─────────┼────────────────────────────────┤
│ sales_2024.csv  │  15000 │  14987 │      13 │ id(int), date(datetime), ...   │
└─────────────────┴────────┴────────┴─────────┴────────────────────────────────┘
```

## Gestion des erreurs

| Situation | Action |
|-----------|--------|
| Fichier CSV vide | Signaler et ignorer |
| Encodage non-UTF-8 | Réessayer avec `latin-1`, puis `cp1252` |
| Colonne sans nom | Nommer `col_0`, `col_1`, etc. |
| Fichier Parquet déjà existant | Écraser avec un avertissement |
| Répertoire `/data/raw/` absent | Lever une erreur explicite et arrêter |

## Dépendances requises

```
pandas>=2.0
pyarrow>=14.0
```

Installation : `pip install pandas pyarrow`
