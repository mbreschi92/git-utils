#!/bin/bash
# Usage: ./go_to_branch.sh nome-branch [--dry-run]
set -euo pipefail

BRANCH=$1
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
    esac
done

if [ -z "$BRANCH" ]; then
    echo "Uso: ./go_to_branch.sh nome-branch [--dry-run]"
    exit 1
fi

git fetch origin

if [ "$DRY_RUN" = true ]; then

    CONTROL_FLAG=false

    # Controllo locale
    if git show-ref --verify --quiet "refs/heads/$TYPE/$NAME"; then
        CONTROL_FLAG=true
    fi

    # Controllo remoto
    if git ls-remote --exit-code --heads origin "$TYPE/$NAME" &>/dev/null; then
        CONTROL_FLAG=true
    fi

    if [ "$CONTROL_FLAG" = false ]; then
        echo "Branch $BRANCH non trovata né in locale né in remoto."
        exit 1
    fi
    
    echo "[DRY RUN] Passaggio alla branch $BRANCH"
    exit 0
fi

# Controlla se la branch esiste in locale
if git show-ref --verify --quiet refs/heads/$BRANCH; then
    git switch $BRANCH
else
    # Se non esiste, prova a crearla dal remoto
    git switch -c $BRANCH origin/$BRANCH 2>/dev/null || {
        echo "Branch $BRANCH non trovata né in locale né in remoto."
        exit 1
    }
fi

echo "Ora sei su $BRANCH"

# TODO show list of branches
# TODO check uncommitted changes