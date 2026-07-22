# API catalog

| API | Route | Exposure | Client |
| --- | --- | --- | --- |
| Accounts | `/accounts/v1` | Internal | Mobile banking |
| Payments | `/payments/v1` | Internal | Payments processor |
| Cards | `/cards/v1` | Internal | Customer web |
| Customer profile | `/customers/v1` | Internal | CRM |
| Fraud decisions | `/fraud/v1` | Internal | Fraud platform |
| Open banking | `/open-banking/v1` | External | Fintech partner |

The internal host is `api.internal.banklab.test`. The external host is
`api.external.banklab.test`.

Each API package is under `apis/synthetic-bank/<api>`. Ownership, routing, and
security metadata live in `apis/synthetic-bank/api-catalog.yaml`.

To add an API, follow [Onboard an API](runbooks/onboard-api.md). Do not copy an
entire existing directory without removing fields that do not apply to the new
service.
