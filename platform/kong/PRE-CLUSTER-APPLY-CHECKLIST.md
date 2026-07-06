# Pre-Cluster Apply Checklist

Use this checklist before requesting approval to apply the Kong OSS baseline.

- Branch is recorded.
- Commit is recorded.
- Working tree state is understood.
- Goal 002 evidence still says `pass; local-only`.
- Kong Gateway remains pinned to `kong:3.9.3`.
- KIC remains pinned to `kong/kubernetes-ingress-controller:3.5.10`.
- Gateway API remains pinned to `v1.3.0`.
- KIC/Gateway API compatibility validation is active.
- `make validate-kong-baseline` passes.
- `make render-kong-baseline` passes.
- `make kong-admin-exposure-test` passes.
- `make runtime-preflight-local` passes.
- `make mutation-guard-test` passes.
- `reports/kong-runtime-apply-plan.md` is current.
- No real secrets, kubeconfigs, private keys, API keys, passwords, or generated
  certificates are committed.
- `BANKLAB_ALLOW_CLUSTER_MUTATION` is not set until explicit approval is given.
- `BANKLAB_TARGET_CONTEXT` is not guessed or defaulted.
