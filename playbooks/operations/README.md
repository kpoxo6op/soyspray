# Operations

Cluster operation playbooks organized by functional area.

## Structure

### nodes/
Node management and configuration playbooks.

- install-node-tools.yml - Install common tools on nodes
- restart-node.yml - Restart cluster nodes
- configure-openwrt-syslog.yml - Configure rsyslog to receive logs from OpenWrt router

### networking/
Network setup and tooling playbooks.

- install-tailscale.yml - Install Tailscale VPN
- remove-tailscale.yml - Remove Tailscale VPN
- publish-headlamp-token.yml - Generate and publish Headlamp token
- set-lan-ingress-hairpin.yml - Let LAN-only devices open `*.soyspray.vip` through OpenWrt

### storage/
Storage initialization and management playbooks.

- initialize-longhorn-storage.yml - Initialize Longhorn storage system
- prepare-longhorn-worker-ssd.yml - repartition, format, and mount new worker SSDs at `/storage` by per-host `/dev/disk/by-id` paths
- prepare-media-usb-disk.yml - repartition, format, mount, and prepare the USB media disk at `/srv/media`

### security/
Security playbooks.

- sync-certificates.yml - Synchronize TLS certificates across namespaces

### android-tv/

[Living-room Android TV](android-tv): debloat, privacy settings, pinned apps
and the router reservation, kept as declared state and synced over ADB.

### boys/

[Private Boys trip bootstrap](boys) from off-cluster Ansible Vault input.

### recovery/

Critical S3 backups, encrypted runtime exports, and isolated restore operations.
See [the recovery guide](recovery).

### retirement/

The [node-0 retirement operation](retirement) verifies that the old
OpenClaw installation is absent. OpenClaw runs on the laptop. Keep this
retryable playbook through the migration window.

### examples/
Example and utility playbooks.

- show-hello.yml - Example playbook demonstrating basic operations

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
