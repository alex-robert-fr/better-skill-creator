# Benchmark : skill-creator

**Modèle** : —
**Date** : 2026-04-01T12:01:48Z
**Evals** : 3 (1 run(s) par config)

## Résumé

| Métrique | With Skill | Without Skill |
|---------|---------|---------|
| Tokens | 9734 ± 9540 | 4406 ± 2445 |
| Pass Rate | 100% ± 0% | 100% ± 0% |
| Temps (s) | 80.5 ± 23.6 | 87.1 ± 19.6 |

## Token Efficiency

- **with_skill** vs without_skill : +5328 tokens, +0.00 pass_rate → **neutre**

## Observations

- Assertion non-discriminante (100% dans toutes les configs) : "Le SKILL.md contient un frontmatter YAML avec les champs 'na..."
- Assertion non-discriminante (100% dans toutes les configs) : "La description du frontmatter mentionne les triggers liés au..."
- Assertion non-discriminante (100% dans toutes les configs) : "Le corps du skill mentionne les 3 catégories de commits : fe..."
- Assertion non-discriminante (100% dans toutes les configs) : "Le skill décrit le format de sortie attendu pour le CHANGELO..."
- Assertion non-discriminante (100% dans toutes les configs) : "Le SKILL.md fait moins de 500 lignes"
- Assertion non-discriminante (100% dans toutes les configs) : "Le skill mentionne les chemins /data/raw/ (input CSV) et /da..."
- Assertion non-discriminante (100% dans toutes les configs) : "Le skill mentionne le format Parquet comme output cible"
- Assertion non-discriminante (100% dans toutes les configs) : "Le skill décrit une stratégie pour gérer les valeurs nulles ..."
- Assertion non-discriminante (100% dans toutes les configs) : "La nouvelle description couvre les triggers 'relecture', 'au..."
- Assertion non-discriminante (100% dans toutes les configs) : "La nouvelle description est plus longue que l'originale ('Re..."
- Assertion non-discriminante (100% dans toutes les configs) : "La nouvelle description reste concise (moins de 500 caractèr..."
- Assertion non-discriminante (100% dans toutes les configs) : "La réponse explique le raisonnement derrière les ajouts (que..."
- [with_skill] coûte +5328 tokens supplémentaires pour seulement +0.00 de gain — à revoir