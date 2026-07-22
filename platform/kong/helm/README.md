# Kong Helm values

[`values-kong-oss-baseline.yaml`](values-kong-oss-baseline.yaml) configures the
pinned Kong Ingress Controller chart for the lab.

The Argo CD application references this file through a multi-source
application. Chart version selection stays in
[`../../../playbooks/argocd/applications/kong-bank-lab/banklab-kong-application.yaml`](../../../playbooks/argocd/applications/kong-bank-lab/banklab-kong-application.yaml),
not in this values file.
