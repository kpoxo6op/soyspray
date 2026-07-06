# OSS Versus Enterprise

This lab uses Kong OSS as the baseline. It must not silently assume Enterprise
or Konnect functionality.

| Capability | Kong OSS baseline position | Replacement pattern in this lab |
| --- | --- | --- |
| Kong RBAC | Not assumed available | Kubernetes RBAC, Git permissions, CODEOWNERS, policy-as-code |
| Kong Workspaces as governance boundary | Not used as OSS governance boundary | Namespaces, Argo CD projects, repo ownership |
| Kong OIDC plugin | Enterprise-only for this lab | Keycloak SSO for tools, JWT plugin for selected API traffic later |
| Request Validator plugin | Enterprise-only for this lab | OpenAPI linting, contract tests, backend validation |
| MTLS Auth plugin | Enterprise-only for this lab | TLS via cert-manager first; later outer-proxy or custom-plugin experiment if required |
| Developer Portal | Not Kong Enterprise portal | Static docs portal generated from Git |
| Audit logs | Not assumed as Kong Enterprise audit feature | Git PRs, CI logs, Argo CD history, Kubernetes events, evidence reports |

## Rule

If a later goal tries to add an Enterprise-only Kong feature, CI should reject
it unless the goal explicitly marks it as a documented gap, experiment, or
non-baseline evaluation.

## Baseline Replacement Model

The bank-like governance model comes from the platform around Kong:

- Kubernetes RBAC and namespaces for runtime separation.
- Git permissions and CODEOWNERS for change approval.
- Argo CD projects for deployment boundaries.
- Policy-as-code for merge and sync gates.
- Keycloak SSO for platform tools.
- Automated tests and generated evidence reports for auditability.
- Runbooks for operations and incident response.

