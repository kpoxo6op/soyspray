# Goal005 RBAC Runtime Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T00:28:33+12:00

Kubernetes context: kubernetes-admin@cluster.local

## kubectl auth can-i checks
| Actor | Namespace | Verb | Resource | Expected | Actual | Result |
| --- | --- | --- | --- | --- | --- | --- |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-accounts` | `get` | `httproutes.gateway.networking.k8s.io` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-accounts` | `create` | `kongplugins.configuration.konghq.com` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-cards` | `get` | `httproutes.gateway.networking.k8s.io` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-cards` | `create` | `kongplugins.configuration.konghq.com` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-customer-profile` | `get` | `httproutes.gateway.networking.k8s.io` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-customer-profile` | `create` | `kongplugins.configuration.konghq.com` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-payments` | `get` | `httproutes.gateway.networking.k8s.io` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-payments` | `create` | `kongplugins.configuration.konghq.com` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-open-banking` | `get` | `httproutes.gateway.networking.k8s.io` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-open-banking` | `create` | `kongplugins.configuration.konghq.com` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `tenant-fraud` | `get` | `httproutes.gateway.networking.k8s.io` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `tenant-fraud` | `create` | `kongplugins.configuration.konghq.com` | `yes` | `yes` | PASS |
| `system:serviceaccount:platform-kong:kong-platform-change-applier` | `platform-kong` | `get` | `configmaps` | `yes` | `yes` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-accounts` | `get` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-accounts` | `list` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-payments` | `get` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-payments` | `list` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-accounts` | `create` | `networkpolicies.networking.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-accounts` | `patch` | `networkpolicies.networking.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `-` | `create` | `kongclusterplugins.configuration.konghq.com` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `-` | `patch` | `clusterroles.rbac.authorization.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `-` | `patch` | `clusterrolebindings.rbac.authorization.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `-` | `patch` | `validatingwebhookconfigurations.admissionregistration.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-payments` | `get` | `httproutes.gateway.networking.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-payments` | `get` | `services` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `tenant-payments` | `get` | `kongplugins.configuration.konghq.com` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-accounts:retail-accounts-api-applier` | `platform-kong` | `get` | `service/banklab-kong-gateway-admin` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-payments` | `get` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-payments` | `list` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-accounts` | `get` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-accounts` | `list` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-payments` | `create` | `networkpolicies.networking.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-payments` | `patch` | `networkpolicies.networking.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `-` | `create` | `kongclusterplugins.configuration.konghq.com` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `-` | `patch` | `clusterroles.rbac.authorization.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `-` | `patch` | `clusterrolebindings.rbac.authorization.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `-` | `patch` | `validatingwebhookconfigurations.admissionregistration.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-accounts` | `get` | `httproutes.gateway.networking.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-accounts` | `get` | `services` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `tenant-accounts` | `get` | `kongplugins.configuration.konghq.com` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-payments:payments-api-applier` | `platform-kong` | `get` | `service/banklab-kong-gateway-admin` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `tenant-fraud` | `get` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `tenant-fraud` | `list` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `tenant-accounts` | `get` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `tenant-accounts` | `list` | `secrets` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `tenant-fraud` | `create` | `networkpolicies.networking.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `tenant-fraud` | `patch` | `networkpolicies.networking.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `-` | `create` | `kongclusterplugins.configuration.konghq.com` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `-` | `patch` | `clusterroles.rbac.authorization.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `-` | `patch` | `clusterrolebindings.rbac.authorization.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `-` | `patch` | `validatingwebhookconfigurations.admissionregistration.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `tenant-accounts` | `get` | `httproutes.gateway.networking.k8s.io` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `tenant-accounts` | `get` | `services` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `tenant-accounts` | `get` | `kongplugins.configuration.konghq.com` | `no` | `no` | PASS |
| `system:serviceaccount:tenant-fraud:risk-compliance-api-applier` | `platform-kong` | `get` | `service/banklab-kong-gateway-admin` | `no` | `no` | PASS |

## Server-side dry-run apply checks
- system:serviceaccount:tenant-accounts:retail-accounts-api-applier server-side dry-run apply in tenant-accounts: PASS
- system:serviceaccount:tenant-payments:payments-api-applier server-side dry-run apply in tenant-payments: PASS
- system:serviceaccount:tenant-fraud:risk-compliance-api-applier server-side dry-run apply in tenant-fraud: PASS
