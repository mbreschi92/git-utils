#!/bin/bash
# Usage: ./merge_to_develop.sh [feature|bugfix] nome-branch [--auto-resolve] [--dry-run]
set -euo pipefail

TYPE=$1
NAME=$2
AUTO_RESOLVE=false
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --auto-resolve) AUTO_RESOLVE=true ;;
        --dry-run) DRY_RUN=true ;;
    esac
done

if [ -z "$TYPE" ] || [ -z "$NAME" ]; then
    echo "Uso: ./merge_to_develop.sh [feature|bugfix] nome-branch [--auto-resolve] [--dry-run]"
    exit 1
fi

if [ "$TYPE" != "feature" ] && [ "$TYPE" != "bugfix" ]; then
    echo "Tipo non valido. Usa feature o bugfix."
    exit 1
fi
BRANCH="$TYPE/$NAME"

git fetch origin
git switch develop
git pull origin develop

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Merge $BRANCH into develop"
    git merge --no-commit --no-ff "$BRANCH"
    git merge --abort
    exit 0
fi

if [ "$AUTO_RESOLVE" = true ]; then
    git merge -X ours "$BRANCH"
else
    git merge "$BRANCH"
fi

git push origin develop
echo "Merge completato su develop."