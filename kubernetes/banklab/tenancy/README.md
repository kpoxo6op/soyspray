# Bank lab tenancy

This package creates one namespace and least-privilege identity boundary for
each sample API domain.

| File | Purpose |
| --- | --- |
| [`namespaces.yaml`](namespaces.yaml) | Tenant namespaces and Pod Security labels |
| [`serviceaccounts.yaml`](serviceaccounts.yaml) | Tenant identities |
| [`roles.yaml`](roles.yaml), [`rolebindings.yaml`](rolebindings.yaml) | Namespaced permissions |
| [`owner-labels-and-annotations.yaml`](owner-labels-and-annotations.yaml) | Ownership metadata policy |
| [`kustomization.yaml`](kustomization.yaml) | Package entry point |

Tenant resources remain separate from the shared Kong platform namespace.
