# Kong Governance Policy

Goal008 adds a small Kubernetes-native policy-as-code guard for Kong plugin
configuration.

The source contract is:

- `platform/governance/kong/policies/kong-plugin-governance.yaml`

The rendered runtime resources are:

- `admissionregistration.k8s.io/v1/ValidatingAdmissionPolicy`
- `admissionregistration.k8s.io/v1/ValidatingAdmissionPolicyBinding`

The policy allows only the Kong OSS plugin families already used by the bank
lab:

- `key-auth`
- `jwt`
- `acl`
- `rate-limiting`
- `correlation-id`
- `response-transformer`

Runtime smoke uses two server-side dry-run fixtures. The safe fixture uses
`response-transformer` and must pass. The unsafe fixture uses
`request-transformer` and must be denied while the policy binding is active.

Rollback removes the binding first, then the policy. After rollback, the unsafe
fixture becomes server-dry-run admissible again, proving the governance control
was removed without creating a live unsafe plugin.
