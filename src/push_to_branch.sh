
#!/bin/bash
# Usage:
#   ./push_to_current_branch.sh "messaggio commit" [file1 file2 ...] [--dry-run]
set -euo pipefail

COMMIT_MSG=$1
shift

DRY_RUN=false
FILES=()

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        *) FILES+=("$arg") ;;
    esac
done

if [ -z "$COMMIT_MSG" ]; then
    echo "Uso: ./push_to_current_branch.sh \"messaggio commit\" [file1 file2 ...] [--dry-run]"
    exit 1
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Branch corrente: $CURRENT_BRANCH"

# controllo push su branch protette
if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "develop" || "$CURRENT_BRANCH" == release/* ]] ; then
    echo "Push non consentito su branch $CURRENT_BRANCH"
    exit 1
fi

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Operazioni:"
    echo "git add ${FILES[*]:-*tutti i file*}"
    echo "git commit -m \"$COMMIT_MSG\""
    echo "git pull origin $CURRENT_BRANCH --rebase"
    echo "git push origin $CURRENT_BRANCH"
    exit 0
fi

# Add files (o tutti se non specificati)
if [ ${#FILES[@]} -eq 0 ]; then
    git add .
else
    git add "${FILES[@]}"
fi

# Commit
git commit -m "$COMMIT_MSG"

# Pull con rebase per evitare conflitti
git pull origin $CURRENT_BRANCH --rebase

# Push
git push origin $CURRENT_BRANCH

echo "Push completato su $CURRENT_BRANCH"

