# Synthetic bank APIs

Six small APIs provide realistic routes for the Kong lab without external
dependencies.

| API | Exposure | Route |
| --- | --- | --- |
| [`accounts`](accounts/) | Internal | `/accounts/v1` |
| [`payments`](payments/) | Internal | `/payments/v1` |
| [`cards`](cards/) | Internal | `/cards/v1` |
| [`customer-profile`](customer-profile/) | Internal | `/customers/v1` |
| [`fraud-decisions`](fraud-decisions/) | Internal | `/fraud/v1` |
| [`open-banking`](open-banking/) | External | `/open-banking/v1` |

[`api-catalog.yaml`](api-catalog.yaml) is the source of truth for ownership,
exposure, gateway, authentication, authorization, and rate-limit metadata.
[`kustomization.yaml`](kustomization.yaml) assembles all API packages for Argo
CD.
