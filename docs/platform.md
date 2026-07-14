# Operating model

The lab copies the useful parts of a bank platform model without pretending a
home cluster is a regulated production environment.

## Ownership

The platform team owns Kong, shared policies, Argo applications, observability,
and the operator runbooks. API teams own their OpenAPI files, mock backends, and
routes inside tenant namespaces.

Repository paths and namespace boundaries are the practical substitute for
Kong Enterprise workspaces and control-plane RBAC.

## Change flow

1. Make the change on a topic branch.
2. Update focused tests and the relevant runbook.
3. Run `make check`.
4. Push the branch.
5. Run `make go` and deploy the Argo definitions through Ansible.
6. Verify Argo, the routes, and the dashboard.
7. Return temporary `targetRevision` values to `HEAD` before merge.

The current state lives in manifests. Runtime evidence belongs in command
output, dashboards, and Git history rather than hand-edited approval files.

## Kong OSS boundary

The lab does not claim Konnect, Kong Manager, Developer Portal, Enterprise RBAC,
or Enterprise workspaces. It uses Gateway API, Kubernetes namespaces, Git
review, Argo CD, policy checks, and Grafana to cover the parts needed for this
lab.

## Data

All customers, account numbers, cards, transactions, and credentials are test
data. Never add real bank data or production secrets.
