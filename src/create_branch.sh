#!/bin/bash
# Usage: ./create_branch.sh [feature|bugfix] nome-branch [--dry-run] [--from-main]
set -euo pipefail

TYPE=$1
NAME=$2
DRY_RUN=false
FROM_MAIN=false

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        --from-main) FROM_MAIN=true ;;
    esac
done

if [ -z "$TYPE" ] || [ -z "$NAME" ]; then
    echo "Uso: ./create_branch.sh [feature|bugfix|release] nome-branch [--dry-run] [--from-main]"
    exit 1
fi

if [ "$TYPE" == "feature" ] || [ "$TYPE" == "bugfix" ] || [ "$TYPE" == "release" ]; then
    BASE="develop"
else
    echo "Tipo non valido. Usa feature, bugfix o release."
    exit 1
fi

if [ "$FROM_MAIN" = true ]; then
    BASE="main"
fi

# Controllo locale
if git show-ref --verify --quiet "refs/heads/$TYPE/$NAME"; then
    echo "Errore: branch locale $TYPE/$NAME già esistente."
    exit 1
fi

# Controllo remoto
if git ls-remote --exit-code --heads origin "$TYPE/$NAME" &>/dev/null; then
    echo "Errore: branch remota $TYPE/$NAME già esistente."
    exit 1
fi

git fetch origin
git switch $BASE
git pull origin $BASE

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Creazione branch $TYPE/$NAME da $BASE"
    exit 0
fi

git switch -c "$TYPE/$NAME"
git push -u origin "$TYPE/$NAME"

if [ "$TYPE" == "release" ]; then
    echo "$NAME" > .last_release
fi

echo "Branch $TYPE/$NAME creata da $BASE e pushata."
