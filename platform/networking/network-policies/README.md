# NetworkPolicy Baseline

This baseline prepares default-deny and explicit-allow patterns for the Kong
bank lab.

NetworkPolicy enforcement depends on the cluster CNI. If the current CNI does
not enforce NetworkPolicy, these manifests can still be stored and reviewed, but
enforcement must be validated later with live traffic tests after the right CNI
is present.

## Intent

- Default deny ingress and egress in platform and tenant namespaces.
- Allow DNS egress as a reusable pattern.
- Prepare GitOps-to-managed-namespace access for future Argo CD operation.
- Prepare observability scrape and ingress-controller placeholders for later
  goals.

Goal 001 does not create Kong-specific allow rules.

## Rollback

If a policy blocks required traffic, revert the Git change and sync Argo CD, or
delete the specific NetworkPolicy during a controlled recovery.

