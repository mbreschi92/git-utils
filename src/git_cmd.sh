#!/bin/bash
# master_git.sh - Menu per lanciare gli script Git

SCRIPTS_DIR="$(dirname "$0")"

show_menu() {
    echo "=============================="
    echo "   Git Automation Menu"
    echo "=============================="
    echo "1) Create Branch"
    echo "2) Go to Branch"
    echo "3) Push to Current Branch"
    echo "4) Merge Feature/Bugfix into Develop"
    echo "5) Merge Develop into Last Release"
    echo "6) Merge Last Release into Main"
    echo "7) Esci"
    echo "=============================="
}

run_script() {
    local script_name=$1
    shift
    local script_path="$SCRIPTS_DIR/$script_name"
    if [ ! -x "$script_path" ]; then
        echo "Script $script_name non trovato o non eseguibile."
        exit 1
    fi
    "$script_path" "$@"
}

while true; do
    show_menu
    read -p "Scegli un'opzione [1-7]: " choice
    case $choice in
        1)
            read -p "Tipo (feature|bugfix|release): " type
            read -p "Nome branch: " name
            read -p "Flag (es. --dry-run): " flags
            run_script "create_branch.sh" "$type" "$name" $flags
            ;;
        2)
            read -p "Nome branch: " branch
            read -p "Flag (es. --dry-run): " flags
            run_script "go_to_branch.sh" "$branch" $flags
            ;;
        3)
            read -p "Messaggio commit: " msg
            read -p "File (opzionale, separati da spazio): " files
            read -p "Flag (es. --dry-run): " flags
            run_script "push_to_branch.sh" "$msg" $files $flags
            ;;
        4)
            read -p "Tipo (feature|bugfix|release): " type
            read -p "Nome branch: " name
            read -p "Flag (es. --auto-resolve --dry-run): " flags
            run_script "merge_branch_into_develop.sh" $type $name $flags
            ;;
        5)
            read -p "Flag (es. --auto-resolve --dry-run): " flags
            run_script "merge_develop_into_release.sh" $flags
            ;;
        6)
            read -p "Flag (es. --auto-resolve --dry-run): " flags
            run_script "merge_last_release_into_main.sh" $flags
            ;;
        7)
            echo "Uscita."
            exit 0
            ;;
        *)
            echo "Opzione non valida."
            ;;
    esac
done