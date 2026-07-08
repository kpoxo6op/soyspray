# Goal: goal-008-kong-governance-policy-as-code

## Approval Source

ChatGPT Pro accepted `goal-007-consumer-onboarding-entitlements` from the
supplied local, runtime, and rollback evidence at evidence commit `2527339`
with runtime source commit `49b80d6`.

The Pro chats then repeatedly stalled while finalizing the full goal body, but
gave consistent guidance for goal008:

- keep goal008 small
- stay OSS/Kubernetes/GitOps compatible
- implement a platform governance control
- use policy-as-code for Kong resources and unsafe plugin configuration
- include demo, runtime evidence, and rollback

## Objective

Implement a small policy-as-code governance control for Kong resources that
prevents unsafe Kong plugin configuration from entering the cluster.

## Required Scope

- Add a Git-managed governance policy contract for Kong plugin allowlisting.
- Render a Kubernetes-native `ValidatingAdmissionPolicy` and
  `ValidatingAdmissionPolicyBinding`.
- Allow only the Kong OSS plugin families already used by the bank lab:
  `key-auth`, `jwt`, `acl`, `rate-limiting`, `correlation-id`, and
  `response-transformer`.
- Include one safe fixture that passes server-side dry-run.
- Include one unsafe fixture that is rejected by admission policy.
- Add local validation and tests proving the rendered policy, binding, fixtures,
  and allowlist are internally consistent.
- Add runtime evidence proving the policy applies, rejects the unsafe fixture,
  allows the safe fixture, and does not break existing goal004/goal005/goal007
  runtime behavior.
- Add rollback evidence proving the admission policy and binding can be removed
  cleanly, and that the unsafe fixture becomes dry-run admissible only after the
  guard is removed.

## Non-Goals

- Do not install Gatekeeper, Kyverno, OPA, or another policy controller.
- Do not use Kong Enterprise or Konnect.
- Do not mutate existing Kong routes or plugins as the success path.
- Do not create real credentials.
- Do not block existing goal004, goal005, goal006, or goal007 resources.
- Do not expose Kong Admin API.

## Completion Gate

Goal008 is complete only when local validation passes, the admission policy is
applied and smoke-tested, rollback passes, evidence is committed and pushed, and
ChatGPT Pro approves the goal as runtime-verified.
