# AGENTS.md

## Project Overview
This repo manages a kubespray-provisioned Kubernetes cluster and its workloads
(Ansible + Argo CD apps). Work often includes cluster operations, logs/alerts,
and backup/retention checks.

## Tools
- `kubectl`: Inspect cluster resources, pods, logs, and CRs.
- `aws` CLI: Check backup objects and IAM policies/permissions when S3 is
  involved.
- `gh` (GitHub CLI): Create/merge PRs and update PR descriptions.
- `ansible-playbook`: Run runbooks with the repo’s inventory and standard
  privilege escalation; check `Makefile` targets for canonical command
  templates.

## Workflow
- Never modify `main` directly. Always work in a branch (PR branch or local
  topic branch) and keep `main` untouched.
- For PR work: check out the PR branch, make changes there, push, then deploy.
- Push changes to the remote before running any deploys or cluster actions.
- Prefer explicit confirmations before destructive cluster actions.
