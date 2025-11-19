#!/bin/bash
# master_git.sh - Menu per lanciare gli script Git

SCRIPTS_DIR="$(dirname "$0")"

show_menu() {
    echo "=============================="
    echo "   Git Automation Menu"
    echo "=============================="
    echo "0) Setup Repository"
    echo "1) Create Branch"
    echo "2) Rename Branch"
    echo "3) Go to Branch"
    echo "4) Push to Current Branch"
    echo "5) Merge Feature/Bugfix into Develop"
    echo "6) Merge Develop into Last Release"
    echo "7) Merge Last Release into Main"
    echo "8) Esci"
    echo "=============================="
}

run_script() {
    local script_name=$1
    shift
    local script_path="$SCRIPTS_DIR/$script_name"

    read -p "Esecuzione $script_name con argomenti: $* (premi Invio per continuare)" dummy
    bash "$script_path" "$@"

    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    echo "Attualmente su branch $CURRENT_BRANCH"
}

while true; do
    show_menu
    read -p "Scegli un'opzione [1-7]: " choice
    case $choice in
        0)
            read -p "Flag (es. --remove): " flags
            run_script "setup_repo.sh" $flags
            ;;
        1)
            read -p "Tipo (feature|bugfix|release): " type
            read -p "Nome branch: " name
            read -p "Flag (es. --dry-run): " flags
            run_script "create_branch.sh" "$type" "$name" $flags
            ;;
        2)
            read -p "Vecchio nome branch: " old_name
            read -p "Nuovo nome branch: " new_name
            run_script "rename_branch.sh" "$old_name" "$new_name"
            ;;
        3)
            read -p "Nome branch: " branch
            read -p "Flag (es. --dry-run): " flags
            run_script "go_to_branch.sh" "$branch" $flags
            ;;
        4)
            read -p "Messaggio commit: " msg
            read -p "File (opzionale, separati da spazio): " files
            read -p "Flag (es. --dry-run): " flags
            run_script "push_to_branch.sh" "$msg" $files $flags
            ;;
        5)
            read -p "Tipo (feature|bugfix|release): " type
            read -p "Nome branch: " name
            read -p "Flag (es. --auto-resolve --dry-run): " flags
            run_script "merge_branch_into_develop.sh" $type $name $flags
            ;;
        6)
            read -p "Flag (es. --auto-resolve --dry-run): " flags
            run_script "merge_develop_into_release.sh" $flags
            ;;
        7)
            read -p "Flag (es. --auto-resolve --dry-run): " flags
            run_script "merge_last_release_into_main.sh" $flags
            ;;
        8)
            echo "Uscita."
            exit 0
            ;;
        *)
            echo "Opzione non valida."
            ;;
    esac
done