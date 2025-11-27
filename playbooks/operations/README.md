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

### storage/
Storage initialization and management playbooks.

- initialize-longhorn-storage.yml - Initialize Longhorn storage system

### security/
Security and certificate management playbooks.

- sync-certificates.yml - Synchronize TLS certificates across namespaces

### examples/
Example and utility playbooks.

- show-hello.yml - Example playbook demonstrating basic operations

## Usage

All playbooks follow standard Ansible execution pattern:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  operations/<category>/<playbook-name>.yml
```

## Naming Convention

Playbooks use `verb-subject.yml` format:
- install-node-tools.yml
- restart-node.yml
- set-node-labels.yml
- initialize-longhorn-storage.yml


