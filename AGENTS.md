# AGENTS.md

## Project Overview
This repo manages a kubespray-provisioned Kubernetes cluster and its workloads
(Ansible + Argo CD apps). Work often includes cluster operations, logs/alerts,
and backup/retention checks.

## Primary Tools
- `kubectl`: Inspect cluster resources, pods, logs, and CRs.
- `aws` CLI: Check backup objects and IAM policies/permissions when S3 is
  involved.
- `gh` (GitHub CLI): Create/merge PRs and update PR descriptions.
