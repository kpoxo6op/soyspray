# Goal008 Governance Policy Rollback Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T02:13:22+12:00

Kubernetes context: kubernetes-admin@cluster.local

Rollback command: make goal008-governance-policy-rollback-and-smoke

Resources removed: ValidatingAdmissionPolicyBinding/banklab-kong-plugin-governance and ValidatingAdmissionPolicy/banklab-kong-plugin-governance

## Rollback output
validatingadmissionpolicybinding.admissionregistration.k8s.io "banklab-kong-plugin-governance" deleted
validatingadmissionpolicy.admissionregistration.k8s.io "banklab-kong-plugin-governance" deleted

## Unsafe fixture server dry-run after rollback
kongplugin.configuration.konghq.com/goal008-denied-request-transformer created (server dry run)

## Runtime smoke after rollback
admission policy and binding removed: pass
unsafe KongPlugin fixture dry-run is admissible after rollback: pass
