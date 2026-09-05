# Operations

Cluster operation playbooks organized by functional area.

## Structure

### nodes/
Node management and configuration playbooks.

- install-node-tools.yml - Install common tools on nodes
- restart-node.yml - Restart cluster nodes
- set-node-labels.yml - Set node labels
- set-resource-limits.yml - Configure resource limits
- configure-openwrt-syslog.yml - Configure rsyslog to receive logs from OpenWrt router

### networking/
Network setup and tooling playbooks.

- install-tailscale.yml - Install Tailscale VPN
- remove-tailscale.yml - Remove Tailscale VPN
- publish-headlamp-token.yml - Generate and publish Headlamp token

### kubernetes/
Kubernetes control-plane and cluster membership operations.

- repair-etcd-peer-url.yml - repair stale etcd member peer URLs so they match the current inventory addresses before an HA stretch

### storage/
Storage initialization and management playbooks.

- initialize-longhorn-storage.yml - Initialize Longhorn storage system
- prepare-longhorn-worker-ssd.yml - repartition, format, and mount new worker SSDs at `/storage` by per-host `/dev/disk/by-id` paths
- prepare-media-usb-disk.yml - repartition, format, mount, and prepare the USB media disk at `/srv/media`

### security/
Security playbooks.

- sync-certificates.yml - Synchronize TLS certificates across namespaces

### recovery/

Critical S3 backups, encrypted runtime exports, and isolated restore operations.
See [the recovery guide](recovery/README.md).

### retirement/

The [node-0 retirement operation](retirement/README.md) verifies that the old
OpenClaw installation is absent. OpenClaw runs on the laptop. Keep this
retryable playbook through the migration window.

### examples/
Example and utility playbooks.

- show-hello.yml - Example playbook demonstrating basic operations

## Usage

All playbooks follow standard Ansible execution pattern:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/<category>/<playbook-name>.yml
```

## Naming Convention

Playbooks use `verb-subject.yml` format:
- install-node-tools.yml
- restart-node.yml
- set-node-labels.yml
- initialize-longhorn-storage.yml
