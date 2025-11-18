#!/bin/bash
# Usage: ./push_to_current_branch.sh [--dry-run]
set -euo pipefail

DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
    esac
done

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ -z "$CURRENT_BRANCH" ]; then
    echo "Impossibile determinare la branch corrente."
    exit 1
fi

#controllo se current_branch è develop o main o release/*
if [[ "$CURRENT_BRANCH" == "develop" || "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == release/* ]]; then
    echo "Errore: non è permesso pushare direttamente sulla branch $CURRENT_BRANCH."
    exit 1
fi

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Push della branch corrente: $CURRENT_BRANCH"
    exit 0
fi

# NOTE : Non controllo se la branch esiste su origin,
# git push creerà la branch se non esiste già.
git push -u origin $CURRENT_BRANCH
echo "Branch $CURRENT_BRANCH pushata su origin."