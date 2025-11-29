#!/bin/bash

_ansible_tags_completion() {
    local cur prev words cword
    _init_completion || return

    # 1. Only provide completion if the previous argument was --tags or -t
    if [[ "$prev" != "--tags" && "$prev" != "-t" ]]; then
        return 0
    fi

    # 2. Search for the playbook file in the arguments
    local playbook=""
    for (( i=1; i < cword; i++ )); do
        local word="${words[i]}"
        local prev_word="${words[i-1]}"

        # Skip arguments that are values for flags like -i or --inventory
        if [[ "$prev_word" == "-i" || "$prev_word" == "--inventory" || "$prev_word" == "--user" || "$prev_word" == "-u" || "$prev_word" == "--private-key" ]]; then
            continue
        fi

        # Heuristic: First .yml/.yaml file that isn't a flag is likely the playbook
        if [[ "$word" == *.yml || "$word" == *.yaml ]] && [[ "$word" != -* ]]; then
            playbook="$word"
            break
        fi
    done

    # 3. If playbook found, parse it for tags
    if [[ -n "$playbook" && -f "$playbook" ]]; then
        # Logic:
        # grep: find lines with "tags:"
        # sed: remove "tags:" prefix, remove [] brackets, replace commas with spaces
        # xargs: split into lines
        # sort -u: unique tags only
        local tags=$(grep "tags:" "$playbook" | sed -e 's/^[[:space:]]*tags://' -e 's/[][]//g' -e 's/,/ /g' | xargs -n1 2>/dev/null | sort -u)

        # Generate completion matches
        COMPREPLY=( $(compgen -W "$tags" -- "$cur") )
    fi
}

# -o default: Falls back to standard filename completion for other arguments
complete -o default -F _ansible_tags_completion ansible-playbook
