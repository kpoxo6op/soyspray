# Autism traits Argo CD application

[`autism-traits-project.yaml`](autism-traits-project.yaml) limits this
application to the `kpoxo6op/soyspray` repository, the `autism-traits`
namespace, and the resource kinds in the static site and dedicated tunnel
package.

[`autism-traits-application.yaml`](autism-traits-application.yaml) reconciles
the [package and operator runbook](../../../../../kubernetes/autism-traits/README.md).
The Ansible role bootstraps the dedicated connector token before it applies the
project and Application. It can replace `targetRevision: HEAD` with a pushed
topic branch during a reviewed deployment.
