# Scripts

This directory contains utility scripts for the project.

## Ansible Autocomplete (`ansible-completion.bash`)

This script provides dynamic tab-completion for Ansible playbook tags.

**How it works:**
1. It triggers when typing `ansible-playbook ... --tags ` or `-t`.
2. It finds the `.yml` playbook file in command arguments.
3. It parses the file for `tags: [tag1, tag2]` lines.
4. It suggests these tags when pressing `<TAB>`.

**Installation:**
The script is automatically sourced in `~/.bashrc` via the following line:
```bash
source ~/code/soyspray/scripts/ansible-completion.bash
```

If autocomplete isn't working, try running `source ~/.bashrc` or restarting the terminal.

## ArgoCD List (`argocd-list.sh`)

A helper script to list ArgoCD applications with formatted output.
Used by the `make alist` command.

## HA Stretch Check (`check-ha-stretch.sh`)

Checks the repo and, optionally, the live cluster for the one-node-loss stretch.

```bash
scripts/check-ha-stretch.sh --expect-current --repo-only
scripts/check-ha-stretch.sh --expect-ha --repo-only --vip 192.168.20.13
scripts/check-ha-stretch.sh --expect-ha --live --vip 192.168.20.13
```
