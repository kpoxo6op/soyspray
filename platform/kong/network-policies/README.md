# Kong network policies

This package starts from default deny and opens only the network paths required
by the gateway and controller.

The individual files cover DNS, Kubernetes API access, controller-to-admin
traffic, proxy ingress, and the smoke upstream. Tenant API egress is managed in
[`../../../kubernetes/banklab/security/`](../../../kubernetes/banklab/security/).

[`kustomization.yaml`](kustomization.yaml) is the package entry point.
