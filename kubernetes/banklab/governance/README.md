# Kong governance

This package restricts `KongPlugin` resources to the plugin types approved for
the lab.

- [`policy.yaml`](policy.yaml) defines the validating admission policy and its
  binding.
- [`kustomization.yaml`](kustomization.yaml) is the package entry point.

An unapproved plugin is rejected by Kubernetes before it can change gateway
behaviour.
