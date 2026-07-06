# Kong Runtime Preflight

Use this runbook before requesting permission to apply the Kong OSS baseline.
It is local-only unless the optional read-only commands are deliberately run.

## Local Checks

1. Confirm the branch:

   ```bash
   git branch --show-current
   ```

2. Confirm the working tree is understood:

   ```bash
   git status --short
   ```

3. Re-run the goal 002 local gate:

   ```bash
   make validate-kong-baseline
   make render-kong-baseline
   make kong-static-test
   make kong-admin-exposure-test
   ```

4. Confirm Gateway API compatibility remains pinned:

   ```bash
   rg "v1.3.0|3.5.10|3.9.3" platform/kong/versions.yaml scripts/validate_kong_baseline.py
   ```

5. Confirm no accidental mutation permission is enabled:

   ```bash
   env | rg '^BANKLAB_(ALLOW_CLUSTER_MUTATION|TARGET_CONTEXT)=' || true
   make mutation-guard-test
   ```

6. Confirm secret hygiene and local validation:

   ```bash
   make validate
   make runtime-preflight-local
   ```

## Optional Read-Only Cluster Checks

Run only when the operator wants live inspection:

```bash
make cluster-readonly-preflight
make kong-readonly-preflight
```

Do not treat these as runtime proof. Runtime proof requires explicit apply and
smoke validation in a later gate.
