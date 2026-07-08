# Self-Service Product Contracts

Goal006 adds a small self-service contract path for one existing API product.

The source of truth is Git:

- `platform/self-service/api-products/accounts-self-service-health-v1.yaml`
- `platform/kong/deck/goal006/accounts-self-service-product.yaml`
- `scripts/render_goal006_product_contract.py`

The contract does not create a new API. It targets the existing `accounts`
synthetic API owned by `retail-accounts`.

Runtime enforcement is intentionally small: a route-scoped OSS
`response-transformer` plugin adds `X-Banklab-Product-Contract` to successful
accounts health responses. Positive and negative curl checks prove the product
marker is applied while goal004 authentication, ACL, correlation ID, rate-limit
headers, and Admin API exposure safety still hold.

Rollback removes only the goal006 marker plugin and restores the stable goal005
accounts route annotation.
