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

- install-tailscale.yml - Install direct Tailscale access on worker nodes without advertising LAN routes
- configure-openwrt-tailnet-gateway.yml - Keep OpenWrt advertising only the soyspray LAN route and remove stale old-LAN redirects
- verify-worker-tailnet.yml - End-to-end worker access checks over `.lan`, Tailscale DNS, SSH, Tailscale ping, and Kubernetes readiness
- remove-tailscale.yml - Remove Tailscale VPN
- publish-headlamp-token.yml - Generate and publish Headlamp token

### storage/
Storage initialization and management playbooks.

- initialize-longhorn-storage.yml - Initialize Longhorn storage system
- prepare-longhorn-worker-ssd.yml - repartition, format, and mount new worker SSDs at `/storage` by per-host `/dev/disk/by-id` paths
- prepare-media-usb-disk.yml - repartition, format, mount, and prepare the USB media disk at `/srv/media`

### security/
Security playbooks.

- sync-certificates.yml - Synchronize TLS certificates across namespaces

### openclaw/
OpenClaw install, runtime, and webhook automation runbooks.

- openclaw-install.yml - one-command bootstrap for host, dependencies, baseline config, kubeconfig, and gateway autostart
- openclaw-remove.yml - one-command teardown (autostart disabled, configs/kubeconfig/host removed)
- configure-openclaw-oauth-token.yml - reconfigure OpenClaw OAuth token using OPENCLAW_OAUTH_ACCESS_TOKEN (and optional OPENCLAW_OAUTH_REFRESH_TOKEN)
- openclaw-enable-file-exec-tools.yml - enable optional `file` and `exec` capabilities without browser automation
- openclaw-enable-tools.yml - enable optional tool capabilities (`file`, `exec`, `browser`) in one run
- openclaw-disable-tools.yml - disable optional tool capabilities (`browser`, `exec`, `file`) in one run
- (legacy single-purpose runbooks available under `openclaw/` for direct invocation)

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
