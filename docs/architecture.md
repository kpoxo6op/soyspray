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
- Longhorn provides replicated persistent volumes and native backup records.
- Stateful applications keep their recovery contract beside their manifests.
- Recovery keys and private bootstrap inputs stay outside the cluster and Git.

The [Argo CD root](https://github.com/kpoxo6op/soyspray/tree/main/argocd)
contains the application catalogue. The [Kubespray inventory](https://github.com/kpoxo6op/soyspray/tree/main/kubespray/inventory/soycluster)
contains the declared cluster membership.

## Incident pipeline

One operational incident produces one investigation and one explanation.

```text
Prometheus rule fires
└── Alertmanager routes the group to Telegram and Healthchecks.io
    └── in-cluster incident loop polls /api/v2/alerts every two minutes
        ├── folds related alerts into one incident (application or node)
        ├── collects bounded read-only evidence from Loki, outside the sandbox
        ├── asks the Jev classifier for a semantic hint (never proof)
        ├── asks DeepSeek for one narrative, with no tools and no cluster access
        └── sends one Telegram narrative, material updates and one recovery
```

Prometheus owns health and paging. Alertmanager owns routing and grouping. Loki
keeps searchable raw evidence. The in-cluster loop owns incident identity and
decides whether an incident is worth a model call. The model is a stateless,
tool-free HTTP request, so it has no cluster credentials, no ability to run code
and no way to change anything. The loop itself has no service account token and
a NetworkPolicy that excludes the API server.

The [Loki alert pipeline](https://github.com/kpoxo6op/soyspray/tree/main/apps/loki/manifests/docs)
records the counter mapping. The
[cluster diagnosis README](https://github.com/kpoxo6op/soyspray/tree/main/apps/cluster-diagnosis)
records the evidence boundary, the spending ledger, the classifier contract and
the rollback steps.
