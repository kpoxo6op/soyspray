# Goal008 Governance Policy Rollout Evidence

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-09T02:13:08+12:00

Kubernetes context: kubernetes-admin@cluster.local

Policy: banklab-kong-plugin-governance

Runtime kind: ValidatingAdmissionPolicy

Validation action: Deny

## Apply output
validatingadmissionpolicy.admissionregistration.k8s.io/banklab-kong-plugin-governance created
validatingadmissionpolicybinding.admissionregistration.k8s.io/banklab-kong-plugin-governance created

## Safe fixture server dry-run
kongplugin.configuration.konghq.com/goal008-allowed-response-transformer created (server dry run)

## Unsafe fixture server dry-run
Error from server (Forbidden): error when creating "STDIN": kongplugins.configuration.konghq.com "goal008-denied-request-transformer" is forbidden: ValidatingAdmissionPolicy 'banklab-kong-plugin-governance' with binding 'banklab-kong-plugin-governance' denied request: KongPlugin plugin must be approved by the banklab Kong governance allowlist.

## Runtime smoke
admission policy and binding applied: pass
safe KongPlugin fixture accepted by server dry-run: pass
unsafe KongPlugin fixture rejected by governance policy: pass
