#!/bin/bash
# setup_repo.sh
# Usage: ./setup_repo.sh [--remove]
set -euo pipefail

REMOVE=false
for arg in "$@"; do
    case $arg in
        --remove) REMOVE=true ;;
    esac
done

git fetch origin

if [ "$REMOVE" = true ]; then
    echo "Rimozione branch non conformi..."
    for branch in $(git branch | sed 's/*//'); do
        if [[ "$branch" != "main" && "$branch" != "develop" && "$branch" != feature/* && "$branch" != bugfix/* && "$branch" != release/* ]]; then
            echo "Elimino branch: $branch"
            git branch -D "$branch"
        fi
    done
    exit 0
fi

# Controllo main
if ! git show-ref --verify --quiet refs/heads/main; then
    echo "Creazione branch main..."
    git switch --orphan main
    git commit --allow-empty -m "Init main"
    git push -u origin main
fi

# Controllo develop
if ! git show-ref --verify --quiet refs/heads/develop; then
    echo "Creazione branch develop..."
    git switch --orphan develop
    git commit --allow-empty -m "Init develop"
    git push -u origin develop
fi

echo "Setup completato: main e develop presenti."