# Synthetic API Runtime Verification Evidence

Goal 003 may be marked runtime-verified only when evidence proves:

- branch and commit
- explicit mutation approval
- target and actual Kubernetes context
- goal 003 local validation result
- server dry-run result
- apply result
- tenant namespace state
- backend Deployment readiness
- backend Service state
- HTTPRoute accepted status and Gateway parent attachment
- NetworkPolicy state
- internal route smoke results
- external open-banking route smoke result
- negative test results for unknown host, unknown route, and exposure policy
- Admin API safety result
- runtime-created secrets summary
- rollback command availability
- `reports/goal-003-summary.md` status
- `reports/gate-003-synthetic-api-runtime-apply-and-smoke-summary.md` status
- `docs/decisions/goal-003-runtime-approval.md` status

If any runtime evidence is missing, failed, blocked, or partial, goal 003 is not
runtime-verified and goal 004 remains blocked.
