# cert-manager Prerequisite

cert-manager will manage TLS lifecycle for later Kong goals. It supports
declarative certificate issuance, renewal, and future short-lived certificate
rotation tests.

Goal 001 does not install cert-manager and does not issue Kong certificates.

## Examples

- `cluster-issuer-selfsigned.example.yaml` shows a self-signed issuer for lab
  bootstrapping.
- `cluster-issuer-banklab-ca.example.yaml` shows the shape of a CA issuer that
  references a future Kubernetes Secret. The secret is not created here.

Do not commit CA private keys. Generate and store CA material outside Git or
through a future SOPS/age workflow.

## Rollback

Rollback should remove the Git change and sync Argo CD, or delete example
issuers if they were manually applied during a controlled test.

## Validation

Local validation parses these manifests and renders the kustomization. Cluster
validation is opt-in.

