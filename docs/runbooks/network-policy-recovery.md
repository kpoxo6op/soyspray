# Runbook: NetworkPolicy Recovery

## Purpose

Recover from a NetworkPolicy that blocks expected platform or tenant traffic.

## Symptoms

- DNS failures.
- GitOps controller cannot reach managed namespaces.
- Future scrape or ingress traffic fails after policy changes.

## Immediate Checks

```sh
kubectl get networkpolicy -A
kubectl describe networkpolicy -n <namespace> <policy>
```

## Mitigation

Identify the narrowest blocking policy. Prefer Git revert and Argo CD sync. For
urgent recovery, delete the specific policy and record the action in an incident
or evidence report.

## Validation

Confirm the affected traffic works again and add a negative/positive test before
reintroducing the policy.

