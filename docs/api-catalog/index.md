# Synthetic API Catalog

| API | Domain | Owner | Namespace | Exposure | Host | Path | Temporary auth posture |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Accounts | `accounts` | tenant-accounts-team | `tenant-accounts` | internal | `api.internal.banklab.test` | `/accounts/v1` | `kong-oss-goal004-auth` |
| Payments | `payments` | tenant-payments-team | `tenant-payments` | internal | `api.internal.banklab.test` | `/payments/v1` | `kong-oss-goal004-auth` |
| Cards | `cards` | tenant-cards-team | `tenant-cards` | internal | `api.internal.banklab.test` | `/cards/v1` | `kong-oss-goal004-auth` |
| Customer Profile | `customer-profile` | tenant-customer-profile-team | `tenant-customer-profile` | internal | `api.internal.banklab.test` | `/customers/v1` | `kong-oss-goal004-auth` |
| Fraud Decisions | `fraud-decisions` | tenant-fraud-team | `tenant-fraud` | internal | `api.internal.banklab.test` | `/fraud/v1` | `kong-oss-goal004-auth` |
| Open Banking Partner | `open-banking` | tenant-open-banking-team | `tenant-open-banking` | external | `api.external.banklab.test` | `/open-banking/v1` | `kong-oss-goal004-auth` |

All examples and responses are synthetic. Authentication, authorization, and rate limiting are deferred to goal 004.
