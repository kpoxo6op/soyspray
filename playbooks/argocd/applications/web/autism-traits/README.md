# Autism traits Argo CD application

[`autism-traits-application.yaml`](autism-traits-application.yaml) reconciles
the [static site package](../../../../../kubernetes/autism-traits/README.md)
in the `default` AppProject.

The Ansible role can replace `targetRevision: HEAD` with a topic branch during
a reviewed deployment.
