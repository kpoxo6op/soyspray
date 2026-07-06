# Runbook: Platform Prerequisite Rollback

## Purpose

Rollback platform prerequisite manifests if a staged or applied prerequisite
breaks expected cluster behaviour.

## Symptoms

- Argo CD sync failure.
- Namespace labels or project boundaries are wrong.
- NetworkPolicy blocks traffic unexpectedly.
- MetalLB or cert-manager examples were applied incorrectly.

## Immediate Checks

```sh
git status
make validate-prereqs
make cluster-prereq-smoke
```

## Mitigation

Use Git revert for reviewed changes. If a live policy breaks traffic, delete the
specific NetworkPolicy as a controlled recovery, then open a follow-up PR with
the evidence.

## Validation

Re-run local validation and any opt-in cluster smoke checks used during the
change.

## Evidence To Collect

- Commit or PR link.
- Failing command output.
- Argo CD sync status if applicable.
- Kubernetes event or policy evidence.

