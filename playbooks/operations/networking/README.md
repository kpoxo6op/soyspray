# Bounded cluster network test

`test-cluster-network.yml` disconnects all three physical LAN interfaces for
10-120 seconds. Use only with explicit outage authorization and merged `main`.
It requires Ready nodes, healthy attached storage and Synced/Healthy applications.
Take and verify an off-cluster etcd snapshot with the existing node operation
before starting. Save pod, storage and mount identities in private evidence.

```bash
source soyspray-venv/bin/activate
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu \
  playbooks/operations/networking/test-cluster-network.yml \
  -e temporary_network_disruption=true -e network_test_seconds=30 \
  -e network_test_id=YYYYMMDDTHHMMSSZ-GIT_SHA
```

Each host runs independently of SSH. A separate systemd timer must be armed
before the interface goes down; an exit trap also restores it on script failure.
The playbook refuses host limits, virtual interfaces and an unexpected source IP.
It preserves disks, addresses, Kubernetes objects and network configuration.
The timers are temporary and contain no credentials. This operation does not
simulate a power loss or prove recovery from hardware faults.

Record availability during the outage, automatic GI audio resumption afterward,
and a real Voice PE command through wake, recognition, light action and reply.
Require all nodes, applications and attached storage recovered before another
test. Keep transcripts/audio and detailed runtime evidence outside this public
repository. Run `pytest tests/test_network_glitch.py` and Ansible syntax/lint checks
before delivery. Rollback means leaving this opt-in operation unused; a running
outage restores locally even if the controller disconnects.
