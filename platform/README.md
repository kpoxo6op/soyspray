# Shared platform resources

This folder contains cluster services shared by application tenants.

- [`kong/`](kong/) contains the optional API gateway platform used by the bank
  lab.

Application-specific workloads stay under [`../apis/`](../apis/) and
[`../kubernetes/`](../kubernetes/) so platform ownership remains visible.
