# Argo CD revision handoff

Return live Applications to `HEAD` after a deployment branch is merged.
This operation changes only matching Git source revisions. It preserves Helm
chart versions, Application settings, resources, and claims.

Fetch the merged history and run the deployment checks from a pushed topic branch:

```bash
git fetch origin
make go
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/argocd/handoff-merged-branch.yml \
  -e handoff_branch=codex/jellyfin-live-tv --check
```

Remove `--check` to apply the handoff. The fetched branch and main must have
identical Git trees. Run it before unrelated changes merge into main.
Each patch checks the Application UID and the observed source before changing
its revision. A concurrent source edit stops that patch. Rerun after inspection.

Check every changed Application with `kubectl -n argocd get applications -o json`.
Inspect both `spec.source` and `spec.sources`. Require the intended revision,
`Synced`, and `Healthy`, then check application access. Delete a merged branch
only after no Application or ApplicationSet references it.

This operation does not change ApplicationSet templates or root manifests.
Do not use it for Applications controlled by those definitions. Update their
source definitions through Git instead. If the operation stops partway through,
retrying changes only the remaining branch references.
