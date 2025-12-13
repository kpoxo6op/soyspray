# Deslop: soyspray

## Objective
Remove AI-generated slop from the current diff against `main` while preserving behavior and repository conventions.

## Inputs
Use the currently staged and unstaged changes in this working tree. Compare against `main`.

## Process
1. Enumerate changed files and group by type:
   - Ansible: `*.yml`, `*.yaml` under `playbooks/` (especially `playbooks/operations/`)
   - ArgoCD/Kubernetes: YAML under `playbooks/argocd/applications/`
   - Docs: `soydocs/` and `README.md`
2. For each changed file, open the closest neighboring file in the same directory and mirror its local conventions (naming, ordering, indentation, and verbosity).
3. Remove slop while preserving intent:
   - Preserve any existing required top-of-file header blocks already used in this repo.
   - Delete comments that restate obvious configuration or duplicate documentation.
   - Delete defensive branches, retries, and fallback defaults that are not present in nearby files serving the same purpose.
   - Replace generic abstractions with the simplest direct expression that matches adjacent code.
   - Delete unused variables, unused labels/annotations, unused kustomize patches, and dead manifests.
4. Keep diffs minimal:
   - Do not reformat unrelated sections.
   - Do not reorder YAML keys unless it removes churn or matches the directory’s dominant pattern.
5. Enforce repo file-creation rules for any newly added YAML/Ansible files:
   - Begin the file with a single multi-line comment header whose first line is the relative path.
   - After the header, keep the file body free of inline comments.

## Repo-specific expectations
- ArgoCD apps live under `playbooks/argocd/applications/<category>/<app>/` and use `kustomization.yaml` to assemble manifests. Ensure referenced resources exist and names align with directory conventions.
- Ansible playbooks live under `playbooks/operations/**` and `playbooks/argocd/**`. Keep tasks idempotent and consistent with existing playbooks in the same folder.
- Prefer existing repo patterns over introducing new tools, new directory layouts, or large refactors.

## Output
Apply the edits.

At the end, print only a 1–3 sentence summary of the changes.
