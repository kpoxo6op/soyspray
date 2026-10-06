# Soyspray operator rules

Kubespray owns the cluster foundation. Argo CD owns application workloads from
`main`. Ansible owns private inputs, secrets, recovery, and deliberate operations.

## Changes

- Work on a branch and deliver through a GitHub pull request. Leave the primary
  checkout on `main`; preserve untracked folders and private inputs.
- GitHub CI is the merge gate. Run affected local checks while developing;
  `make check` runs the complete local gate when needed.
- Use squash merges after CI passes and the change is verified safe. Describe
  what changed, why, risk, and rollback. Verify affected Argo Applications are
  Synced and Healthy after merge.
- Push before running cluster operations. Never make ad hoc imperative cluster
  writes or retarget live Applications to a topic branch.
- Use specific, guarded Ansible operations for destructive changes. Confirm
  scope only when it has not already been authorized. Stop on an unexpected
  state; do not improvise node resets, PVC deletion, or etcd repairs.
- Keep one short README beside each app's source, manifests, tests, and
  operations. Explain purpose, normal use, commands, checks, and limits.
- Keep tests that protect observable behavior, data, security, recovery, and
  deployment safety. Avoid assertions that only mirror source text or prose.

## Data and secrets

- Preserve application data, PVCs, database identities, hostnames, sessions,
  credentials, and node-0's mounted storage and device identities.
- Establish completed backups and isolated restores before moving stateful
  ownership. Adopt and verify replacement paths before deleting definitions.
- Keep root pruning and cascading deletion disabled, including
  `Prune=false,Delete=false`. Protect durable resources from pruning and
  Application deletion. Retirement requires an explicit Ansible operation.
- This repository is public. Never commit secrets, private recovery inputs,
  credentials, or personal context. Use Ansible Vault; keep recovery keys and
  Kubespray `credentials/` private and outside Git. Preserve credentials on retry.
- Put no cluster credentials in GitHub Actions or GitHub secrets.
- Let each backup tool own retention; do not apply generic S3 expiry to active
  backup repositories. A schedule does not prove a completed backup or restore.
- Build custom runtime code into immutable GHCR images. Source-only merges must
  leave running code unchanged; deliver digests through separate promotion PRs.

## Access and operations

- Nodes are `node-0` (`192.168.20.10`), `node-1` (`192.168.20.11`), and `node-2`
  (`192.168.20.12`). Use `make node0`, `make node1`, or `make node2` for SSH as
  `ubuntu`. The API VIP is declared by the inventory.
- Inventory: `inventory/soycluster/hosts.yml`. Activate Ansible with
  `source soyspray-venv/bin/activate` and use the repository's inventory,
  `--become --become-user=root --user ubuntu` conventions.
- Node drills are complete. Follow `playbooks/operations/nodes/README.md` for
  authorized maintenance; do not repeat drills or rebuild evacuation wrappers.
- Use app READMEs for supported checks, comparisons, and isolated restores.
  Read native Argo, Longhorn, CNPG, and Prometheus state. Missing evidence is
  unknown; distinguish configuration, completed backups, and verified restores.
- OpenClaw belongs on the laptop. Keep shared Tailscale access, Kubernetes tools,
  Node.js/npm, and browser tooling, and retain the node-0 retirement operation
  through the migration window.
