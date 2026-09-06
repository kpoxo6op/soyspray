# AGENTS.md

## Project Overview
This repo manages a kubespray-provisioned Kubernetes cluster and its workloads
(Ansible + Argo CD apps). Work often includes cluster operations, logs/alerts,
and backup/retention checks.

## Operator interface

- `make apps` lists Applications and ownership from native metadata.
- `make status APP=boys FORMAT=json` reports source, health, access, and recovery evidence.
- `make check APP=boys`, `make diff APP=boys`, and `make deploy APP=boys` use the app's maintained commands.
- `make backup-status FORMAT=json` reports native backup and restore evidence.
- `make restore-check APP=boys` runs the isolated recovery procedure.
- Use the app README for supported operations and their limits. Missing evidence
  must be unknown with its cause. `make full-check` runs the full repository gate.

Use [operate-soyspray](.agents/skills/operate-soyspray/SKILL.md) for operations and
[change-soyspray-app](.agents/skills/change-soyspray-app/SKILL.md) for app changes.

## Tools
- `kubectl`: Inspect cluster resources, pods, logs, and CRs.
- `aws` CLI: Check backup objects and IAM policies/permissions when S3 is
  involved.
- `gh` (GitHub CLI): Create/merge PRs and update PR descriptions.
- `ansible-playbook`: Run runbooks with the repo’s inventory and standard
  privilege escalation; check `Makefile` targets for canonical command
  templates.

## Node Access
- The cluster has three nodes: node-0 (`192.168.20.10`), node-1
  (`192.168.20.11`), and node-2 (`192.168.20.12`).
- Use `make node0`, `make node1`, or `make node2` for SSH as `ubuntu`.
- Kubespray inventory is `kubespray/inventory/soycluster/hosts.yml`.
- Kubespray owns the cluster foundation. Argo CD owns application workloads;
  Ansible owns bootstrap inputs, secrets, recovery, and deliberate operations.

## Networking Notes
- Router (OpenWrt) is at `192.168.20.1`.
- LAN subnet: `192.168.20.0/24`.
- DNS override: `soyspray.vip` resolves to `192.168.20.20` via router dnsmasq.
- Tailscale on the router advertises the LAN route `192.168.20.0/24` and forwards
  `tailscale -> lan`.

## Workflow
- Never run imperative commands modifying the cluster. Make changes in code.
- Never modify `main` directly. Always work in a branch (PR branch or local
  topic branch) and keep `main` untouched. Exception: markdown and comments.
- For PR work: check out the PR branch, make changes there, push, then deploy.
- Push changes to the remote before running any deploys or cluster actions.
- Normal `make deploy APP=NAME` runs shared checks, affected-app checks, and
  deployment preflight. Run `make go` for shared changes and final verification.
- Activate the venv via `make act` before running Ansible.
- For non-interactive runs, use:
  `source soyspray-venv/bin/activate && ansible-playbook ...`.
- For an adopted app, keep committed Git sources at `HEAD` and use the native
  root preview procedure to select one pushed branch. Return the root to `HEAD`
  after merge and verify the exact child comparison. Legacy apps still use their
  documented revision input until adoption; do not leave temporary branches live.
- When work creates or changes a feature folder, add or update a short,
  human-centered `README.md` in that folder. Explain its purpose, normal human
  use, important commands, checks, and limits. Keep shared indexes concise.
- Use specific Ansible operations for destructive changes. Confirm scope when
  it is not already authorized; preserve shared resources and access.
- Keep tests that protect behavior, data, ownership, and deployment safety.
  Tests need not precede implementation. Do not enforce prose or file counts.

## Application and data protection

- Keep app manifests, configuration, source, tests, and a short README under
  `apps/NAME/`. Use upstream charts or Kustomize and explicit native Argo children.
- Build custom runtime code into immutable GHCR images. Source changes open a
  separate digest promotion PR; source-only merges must not change running code.
- Establish backups and isolated restores before moving stateful ownership.
  Preserve names, PVCs, database identities, hostnames, sessions, and keys.
- Adopt and verify replacement paths before deleting old definitions. Check every
  live Application source and referenced values path before cleanup.
- Keep root pruning and cascading deletion disabled. Protect durable resources
  from pruning and Application deletion. Parking retains data; retirement is an
  explicit Ansible operation.
- Use Ansible Vault and documented private bootstrap inputs. Keep recovery keys
  outside the cluster. Preserve existing credentials during retries.
- Each backup tool owns retention. Do not apply generic S3 expiry to active backup
  repositories. A schedule alone does not prove the recovery target.

## Pull Request Standard
- Organize commits for review before opening or substantially updating a PR.
- Keep a normal commit to one leaf folder or 1-5 closely related files. Aim for
  roughly 2-3 screens of ordinary changes when that is practical.
- Use smaller one-file commits for lifecycle switches, security boundaries,
  deployment controls, and other logic that deserves focused review.
- Do not mix platform code, application code, documentation, tests, generated
  artifacts, or vendored material when those concerns can be reviewed
  independently.
- Put an unavoidable large generated or vendored file in its own commit. State
  what it is in the commit subject instead of hiding it inside a broad commit.
- Rebase onto the current base branch before final review. When history must be
  rewritten, preserve the delivered tree, run the full local gate, and use
  `--force-with-lease` rather than an unrestricted force push.
- Write the PR description in simple, neutral English. Lead with the outcome
  and safety facts, then include a review map, exact operating commands,
  verification evidence, and rollback instructions when relevant.
- List every commit from oldest to newest with a direct GitHub commit link.
- Run affected-app CI and shared checks. Cancel superseded runs; preserve an
  explicit full-repository check.
- For a large PR, group commit ranges by area and place the complete commit list
  in a collapsible section so the main description stays readable.
- Add line-anchored PR comments where code is hard or non-obvious. Explain the
  reason in simple English, not just what the line says.
- After a force push, verify every inline comment against the new head. Replace
  comments that are outdated or no longer line-anchored.
- Keep the PR in draft until the description matches the current head and all
  required local and GitHub checks pass.
- Exclude one-off reports, temporary evidence, generated screenshots, secrets,
  personal context, and irrelevant employer or client names from the PR.

## Laptop operations
- OpenClaw runs on the laptop. Do not install it on cluster nodes.
- Keep shared Tailscale access, Kubernetes tools, Node.js/npm, and browser tooling.
- Keep `playbooks/operations/retirement/node0-openclaw.yml` through the migration
  window. It verifies absence without revoking credentials shared with the laptop.
