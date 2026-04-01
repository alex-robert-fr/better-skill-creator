#!/bin/bash
# Vérifie que le code Python est propre avant de terminer
# Ne tourne que s'il y a des fichiers Python dans le projet
if find . -name "*.py" -not -path "./.git/*" | grep -q .; then
  ruff check . 2>&1
fi
