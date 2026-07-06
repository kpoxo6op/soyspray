# Synthetic API Smoke Plan

Generated at: 2026-07-06T22:22:14+12:00

Status: pass; local-plan

| API | host | path | expected status | expected marker | gateway | tenant namespace | service | client persona | negative cases |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| accounts | `api.internal.banklab.test` | `/accounts/v1/health` | 200 | `banklab-accounts-ok` | `platform-kong/kong-internal` | `tenant-accounts` | `banklab-accounts-api` | `mobile-banking-app` | `api.external.banklab.test/accounts/v1/health` -> 404; `api.internal.banklab.test/accounts/v1/does-not-exist` -> 404 |
| payments | `api.internal.banklab.test` | `/payments/v1/health` | 200 | `banklab-payments-ok` | `platform-kong/kong-internal` | `tenant-payments` | `banklab-payments-api` | `payments-processor` | `api.external.banklab.test/payments/v1/health` -> 404; `api.internal.banklab.test/payments/v1/does-not-exist` -> 404 |
| cards | `api.internal.banklab.test` | `/cards/v1/health` | 200 | `banklab-cards-ok` | `platform-kong/kong-internal` | `tenant-cards` | `banklab-cards-api` | `internet-banking-web` | `api.external.banklab.test/cards/v1/health` -> 404; `api.internal.banklab.test/cards/v1/does-not-exist` -> 404 |
| customer-profile | `api.internal.banklab.test` | `/customers/v1/health` | 200 | `banklab-customer-profile-ok` | `platform-kong/kong-internal` | `tenant-customer-profile` | `banklab-customer-profile-api` | `internal-crm` | `api.external.banklab.test/customers/v1/health` -> 404; `api.internal.banklab.test/customers/v1/does-not-exist` -> 404 |
| fraud-decisions | `api.internal.banklab.test` | `/fraud/v1/health` | 200 | `banklab-fraud-decisions-ok` | `platform-kong/kong-internal` | `tenant-fraud` | `banklab-fraud-decisions-api` | `fraud-platform` | `api.external.banklab.test/fraud/v1/health` -> 404; `api.internal.banklab.test/fraud/v1/does-not-exist` -> 404 |
| open-banking | `api.external.banklab.test` | `/open-banking/v1/health` | 200 | `banklab-open-banking-ok` | `platform-kong/kong-external` | `tenant-open-banking` | `banklab-open-banking-api` | `external-fintech-partner` | `api.internal.banklab.test/open-banking/v1/health` -> 404; `api.external.banklab.test/open-banking/v1/does-not-exist` -> 404 |
