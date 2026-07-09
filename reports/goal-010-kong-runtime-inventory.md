# Goal010 Kong Runtime Inventory

Status: pass

Generated at: 2026-07-09T13:59:17+12:00
Kubernetes context: kubernetes-admin@cluster.local
Runtime source commit: 9b35308
Expected inventory file: `soydocs/kong-bank-lab/goal-010-expected-runtime-inventory.yaml`
Expected rendered inventory: `reports/goal-010-expected-runtime-inventory-rendered.yaml`

## Live accounts route
- Resource: `tenant-accounts/HTTPRoute/banklab-accounts`
- Plugin annotation: `banklab-key-auth,banklab-acl,banklab-rate-limit,banklab-correlation-id`

## Live KongPlugin inventory
- `tenant-accounts/KongPlugin/banklab-acl`: `acl`
- `tenant-accounts/KongPlugin/banklab-correlation-id`: `correlation-id`
- `tenant-accounts/KongPlugin/banklab-key-auth`: `key-auth`
- `tenant-accounts/KongPlugin/banklab-rate-limit`: `rate-limiting`
- `tenant-cards/KongPlugin/banklab-acl`: `acl`
- `tenant-cards/KongPlugin/banklab-correlation-id`: `correlation-id`
- `tenant-cards/KongPlugin/banklab-key-auth`: `key-auth`
- `tenant-cards/KongPlugin/banklab-rate-limit`: `rate-limiting`
- `tenant-customer-profile/KongPlugin/banklab-acl`: `acl`
- `tenant-customer-profile/KongPlugin/banklab-correlation-id`: `correlation-id`
- `tenant-customer-profile/KongPlugin/banklab-key-auth`: `key-auth`
- `tenant-customer-profile/KongPlugin/banklab-rate-limit`: `rate-limiting`
- `tenant-fraud/KongPlugin/banklab-acl`: `acl`
- `tenant-fraud/KongPlugin/banklab-correlation-id`: `correlation-id`
- `tenant-fraud/KongPlugin/banklab-key-auth`: `key-auth`
- `tenant-fraud/KongPlugin/banklab-rate-limit`: `rate-limiting`
- `tenant-open-banking/KongPlugin/banklab-acl`: `acl`
- `tenant-open-banking/KongPlugin/banklab-correlation-id`: `correlation-id`
- `tenant-open-banking/KongPlugin/banklab-jwt`: `jwt`
- `tenant-open-banking/KongPlugin/banklab-rate-limit`: `rate-limiting`
- `tenant-payments/KongPlugin/banklab-acl`: `acl`
- `tenant-payments/KongPlugin/banklab-correlation-id`: `correlation-id`
- `tenant-payments/KongPlugin/banklab-key-auth`: `key-auth`
- `tenant-payments/KongPlugin/banklab-rate-limit`: `rate-limiting`

## Live KongConsumer inventory
- `synthetic-clients/KongConsumer/external-fintech-partner` credentials=['<redacted>', '<redacted>']
- `synthetic-clients/KongConsumer/fraud-platform` credentials=['<redacted>', '<redacted>']
- `synthetic-clients/KongConsumer/internal-crm` credentials=['<redacted>', '<redacted>']
- `synthetic-clients/KongConsumer/internet-banking-web` credentials=['<redacted>', '<redacted>']
- `synthetic-clients/KongConsumer/mobile-banking-app` credentials=['<redacted>', '<redacted>']
- `synthetic-clients/KongConsumer/payments-processor` credentials=['<redacted>', '<redacted>']

## Absence checks
- `banklab-goal009-security-headers` absent: pass
- `banklab-kong-plugin-governance` admission resources absent: pass
- `request-transformer` absent: pass
- Kong Admin API exposure safety: pass
