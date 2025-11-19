#!/bin/bash
# rename_branch.sh
# Usage: ./rename_branch.sh vecchio_nome nuovo_nome
set -euo pipefail

OLD=$1
NEW=$2

if [ -z "$OLD" ] || [ -z "$NEW" ]; then
    echo "Uso: ./rename_branch.sh vecchio_nome nuovo_nome"
    exit 1
fi

if [[ "$OLD" == "main" || "$OLD" == "develop" || "$OLD" == release/* ]]; then
    echo "❌ Non puoi rinominare branch protetta: $OLD"
    exit 1
fi

git fetch origin

# Controllo esistenza branch
if ! git show-ref --verify --quiet refs/heads/$OLD; then
    echo "Branch $OLD non trovata."
    exit 1
fi

# Rinominare locale
git branch -m "$OLD" "$NEW"

# Aggiornare remoto
git push origin :"$OLD"
git push -u origin "$NEW"

echo "Branch rinominata da $OLD a $NEW."