# Goal004 Security Smoke Results

Status: pass

Supported states: not run, pass, fail, blocked, partial

Generated at: 2026-07-08T23:14:07+12:00

Kubernetes context: kubernetes-admin@cluster.local

Credential source: local environment variables

## Route checks
api.internal.banklab.test/accounts/v1/health: pass; client=mobile-banking-app; status=200; marker=banklab-accounts-ok; correlation-id=present; rate-limit-headers=present
api.internal.banklab.test/payments/v1/health: pass; client=payments-processor; status=200; marker=banklab-payments-ok; correlation-id=present; rate-limit-headers=present
api.internal.banklab.test/cards/v1/health: pass; client=internet-banking-web; status=200; marker=banklab-cards-ok; correlation-id=present; rate-limit-headers=present
api.internal.banklab.test/customers/v1/health: pass; client=internal-crm; status=200; marker=banklab-customer-profile-ok; correlation-id=present; rate-limit-headers=present
api.internal.banklab.test/fraud/v1/health: pass; client=fraud-platform; status=200; marker=banklab-fraud-decisions-ok; correlation-id=present; rate-limit-headers=present
api.external.banklab.test/open-banking/v1/health: pass; client=external-fintech-partner; status=200; marker=banklab-open-banking-ok; correlation-id=present; rate-limit-headers=present
