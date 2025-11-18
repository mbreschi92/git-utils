#!/bin/bash
# Usage: ./merge_develop_into_release.sh nome-release [--auto-resolve] [--dry-run]
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
    RELEASE=$(cat .last_release)
else
    RELEASE=$(git branch --list 'release/*' | sed 's/.*release\///' | sort -V | tail -n 1)
fi

if [ -z "$RELEASE" ]; then
    echo "Nessuna release trovata."
    exit 1
fi

echo "Ultima release: release/$RELEASE"

git fetch origin
git switch "release/$RELEASE"
git pull origin "release/$RELEASE"

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Merge develop into release/$RELEASE"
    git merge --no-commit --no-ff develop
    git merge --abort
    exit 0
fi

if [ "$AUTO_RESOLVE" = true ]; then
    git merge -X ours develop
else
    git merge develop
fi

git push origin "release/$RELEASE"
echo "Merge completato su release/$RELEASE."