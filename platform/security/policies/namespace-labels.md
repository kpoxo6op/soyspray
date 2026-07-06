# Namespace Label Policy

Every bank-lab namespace must include:

- `banklab.konghq.com/managed-by`
- `banklab.konghq.com/platform-layer`
- `banklab.konghq.com/environment`
- `banklab.konghq.com/data-classification`
- `banklab.konghq.com/owner`

For goal 001:

- `managed-by` must be `gitops`.
- `platform-layer` must be `prereq`.
- `environment` must be `lab`.
- `data-classification` must be `synthetic`.
- `owner` must be non-empty.

