# Node operations

Kubespray owns node removal and readd. The maintained native exercise is
[the drill-v2 guide](drill-v2/README.md). It documents retained-OS removal and
reconciliation for one node at a time.

Other supported node operations are:

- [`snapshot-etcd.yml`](snapshot-etcd.yml) for an etcd snapshot.
- [`monitoring-replicas.yml`](../storage/monitoring-replicas.yml) for the
  disposable monitoring-volume policy.
- The recovery procedures under [`../recovery/`](../recovery/).

Do not use ad hoc node limits, a storage evacuation ceremony, or a host cleanup
wrapper. Keep the complete inventory and run the pinned Kubespray playbooks.
