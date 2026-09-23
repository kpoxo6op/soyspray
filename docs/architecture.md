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
- Argo CD owns declared workloads and follows the reviewed `main` branch.
- Monitoring configuration is moving from the non-pruning stack Application to
  a narrowly scoped child. During the first migration change, existing
  dashboards and rules remain live while the stack releases their declarations.
- Longhorn provides replicated persistent volumes and native backup records.
- Stateful applications keep their recovery contract beside their manifests.
- Recovery keys and private bootstrap inputs stay outside the cluster and Git.

The [Argo CD root](https://github.com/kpoxo6op/soyspray/tree/main/argocd)
contains the application catalogue. The [Kubespray inventory](https://github.com/kpoxo6op/soyspray/tree/main/kubespray/inventory/soycluster)
contains the declared cluster membership.

## Incident pipeline

Prometheus owns health detection. Alertmanager sends native critical and warning
alerts to Telegram and the independent Watchdog route. The in-cluster incident
loop polls Alertmanager, groups related alerts and reads bounded Loki samples.
It sends a factual supplement only when it observes a distinct failure phrase
or a supported relationship between alerts. Missing evidence is unknown;
absence of an alert does not establish recovery. The loop has no AI provider,
classifier or Kubernetes service account token.

The [cluster diagnosis README](https://github.com/kpoxo6op/soyspray/tree/main/apps/cluster-diagnosis)
records message rules, evidence limits, operating commands and rollback.
