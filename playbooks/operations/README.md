# Operations

Cluster operation playbooks organized by functional area.

## Structure

Each directory has its own README with the current playbooks.

### agents/
Private evidence intake for agent workloads. See [agents](agents/README.md).

### android-tv/
Living-room Android TV state, synced over ADB. See [android-tv](android-tv/README.md).

### boys/
Private Boys trip bootstrap. See [boys](boys/README.md).

### networking/
Network setup and tooling. See [networking](networking/README.md).

### nodes/
Node management and configuration. See [nodes](nodes/README.md).

### recovery/
Backups and isolated restore operations. See [recovery](recovery/README.md).

### retirement/
Retirement operations. See [retirement](retirement/README.md).

### security/
Security maintenance. See [security](security/README.md).

### storage/
Storage preparation and management. See [storage](storage/README.md).

### voice/
Bounded voice pipeline tests. See [voice](voice/README.md).

## Usage

All playbooks follow standard Ansible execution pattern:

```bash
ansible-playbook -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/<category>/<playbook-name>.yml
```

## Naming Convention

Playbooks use `verb-subject.yml` format:
- install-node-tools.yml
- restart-node.yml
- initialize-longhorn-storage.yml

## Foundation

Use the [stock upstream inventory guide](../../inventory/soycluster/README.md).
The broken top-level wrapper, label patch, resource patch and one-off etcd repair
are retired. Node labels and OIDC belong to inventory; workloads follow their
Argo owners. Host utilities never replace Kubespray component binaries.
