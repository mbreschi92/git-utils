#!/bin/bash
# Usage: ./merge_release_into_main.sh [--auto-resolve] [--dry-run]
set -euo pipefail

AUTO_RESOLVE=false
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --auto-resolve) AUTO_RESOLVE=true ;;
        --dry-run) DRY_RUN=true ;;
    esac
done

if [ -f ".last_release" ]; then
    LAST_RELEASE=$(cat .last_release)
else
    LAST_RELEASE=$(git branch --list 'release/*' | sed 's/.*release\///' | sort -V | tail -n 1)
fi

if [ -z "$LAST_RELEASE" ]; then
    echo "Nessuna release trovata."
    exit 1
fi

echo "Ultima release: release/$LAST_RELEASE"

git fetch origin
git switch main
git pull origin main

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Merge release/$LAST_RELEASE into main"
    git merge --no-commit --no-ff "release/$LAST_RELEASE"
    git merge --abort
    exit 0
fi

if [ "$AUTO_RESOLVE" = true ]; then
    git merge -X ours "release/$LAST_RELEASE"
else
    git merge "release/$LAST_RELEASE"
fi

git push origin main
echo "Merge completato su main."