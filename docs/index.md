# Soyspray Kong OSS Bank Lab

This documentation site describes the repository foundation for the Kong OSS
bank-lab platform.

The lab will simulate a bank-style platform team running Kong OSS on Kubernetes.
It will use Git as the source of truth, local validation gates, GitOps, policy
checks, automated tests, evidence reports, and runbooks.

Goal 000 is local-only. It creates structure and standards. It does not install
Kong, deploy Kubernetes resources, create secrets, or change the live cluster.

## Local Gates

Run these commands before treating goal 000 as complete:

```sh
make validate
make test
make policy-test
make docs
make evidence
```

## Key Documents

- [Platform principles](architecture/platform-principles.md)
- [OSS versus Enterprise boundary](architecture/oss-vs-enterprise.md)
- [Operating model](architecture/operating-model.md)
- [Testing strategy](architecture/testing-strategy.md)
- [ADR 0001](adr/0001-platform-direction.md)

