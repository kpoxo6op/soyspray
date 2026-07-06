# Certificate Management

cert-manager will support later Kong TLS work through declarative certificate
issuance and renewal.

Goal 001 creates cert-manager prerequisite examples only. It does not install
cert-manager, create a CA private key, or issue Kong certificates.

## Lab Issuers

The self-signed issuer example is useful for bootstrap experiments. The CA
issuer example references a future secret and must not be used until that secret
is created through a safe workflow.

## Later Rotation

Later goals can use short-lived lab certificates to test renewal, alerting, and
rollback paths.

