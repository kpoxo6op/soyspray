# Architecture

Soyspray separates ownership so that routine application delivery does not
silently change the cluster foundation.

```text
Git pull request
├── Kubespray and Ansible -> nodes, bootstrap inputs, recovery operations
└── Argo CD               -> application workloads from main
    └── application       -> manifests, checks, data and recovery contract
```

## Main boundaries

- The cluster has three nodes so ordinary maintenance can preserve service
  while one node is unavailable.
- Kubespray owns Kubernetes installation and cluster-wide configuration.
- Argo CD owns declared workloads and follows the reviewed `main` branch,
  including cert-manager controllers, CRDs and certificate configuration.
- The monitoring stack and CRDs retain non-pruning owners. A separate
  `prometheus-config` child may prune only generated dashboards and custom
  alert rules in `monitoring`, so Git removal and rollback remove those inputs.
- Longhorn provides replicated persistent volumes and native backup records.
- Stateful applications keep their recovery contract beside their manifests.
- Recovery keys and private bootstrap inputs stay outside the cluster and Git.

The [Argo CD root](https://github.com/kpoxo6op/soyspray/tree/main/argocd)
contains the application catalogue. The [Kubespray inventory](https://github.com/kpoxo6op/soyspray/tree/main/inventory/soycluster)
contains the declared cluster membership. The provisioner is upstream Kubespray
v2.31.0. Its cert-manager addon stays disabled; Argo owns the adopted v1.17.1
controllers. [Inventory operations](https://github.com/kpoxo6op/soyspray/tree/main/inventory/soycluster)
cover full reconciliation, Authentik inputs and tag upgrades.

## Incident pipeline

Prometheus owns health detection. Alertmanager sends native critical and warning
alerts to Telegram and keeps the independent Watchdog route. Alloy exports
bounded failure counters and sends searchable logs to Loki. Inspect logs in
Grafana when an alert needs context. Missing evidence is unknown; absence of an
alert does not establish recovery. There is no supplemental diagnosis writer.

Argo CD also owns its own pinned runtime through `apps/argocd/`. Its private
Secrets, controller ConfigMaps and customized server Service/Ingress remain
Ansible inputs. Kubespray Argo and cert-manager addons stay explicitly disabled.
