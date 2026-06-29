# 2026-06-29 Worker Tailnet Prep

## Context

The cluster now has three Kubernetes nodes on the OpenWrt-managed LAN:

| Node | LAN IP | Tailnet state |
| --- | --- | --- |
| `node-0` | `192.168.20.10` | Direct Tailscale machine, Funnel enabled |
| `node-1` | `192.168.20.11` | Direct Tailscale machine and reachable through OpenWrt subnet route |
| `node-2` | `192.168.20.12` | Direct Tailscale machine and reachable through OpenWrt subnet route |

OpenWrt should remain the only subnet router for `192.168.20.0/24`. Do not
advertise LAN routes from `node-1` or `node-2`; direct Tailscale on the worker
nodes is for machine identity and direct host access only.

## Timeline

- `2026-06-29 23:05 NZST`: Tailscale DNS had only
  `soyspray.vip -> 100.96.77.28` as split DNS. Added split DNS
  `lan -> 100.96.77.28` in the Tailscale admin console so remote tailnet
  clients can resolve OpenWrt DHCP names such as `node-1.lan` and `node-2.lan`.
- `2026-06-29 23:05 NZST`: OpenWrt was advertising
  `192.168.20.0/24` and a redundant pending `192.168.20.20/32` route. Ran
  `tailscale set --advertise-routes=192.168.20.0/24` on OpenWrt so only the
  approved LAN route remains.
- `2026-06-29 23:05 NZST`: Deleted two stale OpenWrt WAN redirects named
  `qbittorrent-in` and `qbittorrent-k8s` that still pointed to old
  `192.168.1.x` hosts, then reloaded the firewall. Existing current redirects
  to `192.168.20.20` were left intact.
- `2026-06-29 23:05 NZST`: Disabled Tailscale key expiry on `node-0` ahead of
  worker enrollment.
- `2026-06-29 23:05 NZST`: Refactored
  `playbooks/operations/networking/install-tailscale.yml` for direct worker
  enrollment. It defaults to `node-1:node-2`, keeps `accept-dns=false`,
  `accept-routes=false`, `ssh=false`, and `advertise-routes=[]`.
- `2026-06-29 23:10 NZST`: Generated a temporary reusable auth key in the
  Tailscale admin console, used it once through the worker enrollment playbook,
  and revoked it immediately afterward.
- `2026-06-29 23:12 NZST`: Enrolled the workers as direct machines:
  `node-1.shark-garibaldi.ts.net` at `100.123.125.4` and
  `node-2.shark-garibaldi.ts.net` at `100.103.213.105`.
- `2026-06-29 23:13 NZST`: Disabled key expiry on `node-1` and `node-2`.
- `2026-06-29 23:15 NZST`: Verified SSH by LAN IP through the subnet router,
  SSH by `node-1.lan` and `node-2.lan`, SSH by Tailscale DNS name, and direct
  `tailscale ping` to both workers.
- `2026-06-29 23:15 NZST`: `kubectl get nodes -o wide` showed `node-0`,
  `node-1`, and `node-2` all `Ready` after the Tailscale install.
- `2026-06-29 23:25 NZST`: Added repeatable playbooks for OpenWrt gateway
  reconciliation, worker tailnet enrollment, and worker tailnet verification.
  Verified the OpenWrt and worker playbooks are idempotent with `changed=0`.

## Imperative Changes Performed

These changes were made live before or alongside the repo updates. This section
exists so the live state is not mistaken for something that arrived only from
Git.

| Area | Live change | How it was done | Repeatable coverage |
| --- | --- | --- | --- |
| Tailscale DNS | Added split DNS `lan -> 100.96.77.28` | Tailscale admin console, DNS page | Verified by `verify-worker-tailnet.yml` through `node-1.lan` and `node-2.lan`; not currently configured by Ansible |
| OpenWrt Tailscale | Removed redundant advertised route `192.168.20.20/32`; kept only `192.168.20.0/24` | `ssh root@192.168.20.1 'tailscale set --advertise-routes=192.168.20.0/24'` | Enforced by `configure-openwrt-tailnet-gateway.yml` |
| OpenWrt firewall | Removed stale WAN redirects `qbittorrent-in` and `qbittorrent-k8s` pointing to old `192.168.1.x` hosts | OpenWrt UCI delete/commit plus firewall reload | Enforced by `configure-openwrt-tailnet-gateway.yml` |
| Tailscale machines | Disabled key expiry for `node-0`, `node-1`, and `node-2` | Tailscale admin console, Machines page | Verified by `verify-worker-tailnet.yml`; disabling expiry for a brand-new replacement remains a manual admin-console step |
| Tailscale auth key | Generated a temporary reusable auth key for worker enrollment and revoked it after use | Tailscale admin console, Keys page | No secret is stored in Git; future replacement uses a fresh temporary `TS_AUTH_KEY` |
| Worker nodes | Installed Tailscale and enrolled `node-1` and `node-2` as direct machines | `playbooks/operations/networking/install-tailscale.yml` with temporary `TS_AUTH_KEY` | Re-runnable via `install-tailscale.yml`; already-enrolled nodes do not require `TS_AUTH_KEY` |

No Tailscale auth key, API token, or OAuth client secret was written to this
repo. The only documented key values are redacted placeholders.

## Direct Worker Enrollment

For a fresh replacement node, generate a temporary Tailscale auth key in the
admin console, run the worker enrollment playbook, then revoke the key. Do not
store the key in the repo.

```sh
source soyspray-venv/bin/activate
TS_AUTH_KEY='tskey-auth-REDACTED' ansible-playbook \
  -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/networking/install-tailscale.yml \
  -e tailscale_target_hosts=node-1
```

Run the e2e verifier after enrollment:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/networking/verify-worker-tailnet.yml \
  -e tailscale_target_hosts=node-1
```

OpenWrt gateway guardrails can be reconciled separately if networking looks
off:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  playbooks/operations/networking/configure-openwrt-tailnet-gateway.yml
```

After enrollment, disable key expiry on the new machine in the Tailscale admin
console. The temporary manual key used during the 2026-06-29 prep run was
revoked.

## Observed State After Enrollment

| Node | Tailscale DNS | Tailscale IPv4 | Worker prefs |
| --- | --- | --- | --- |
| `node-1` | `node-1.shark-garibaldi.ts.net` | `100.123.125.4` | `accept-dns=false`, `accept-routes=false`, `ssh=false`, no advertised routes |
| `node-2` | `node-2.shark-garibaldi.ts.net` | `100.103.213.105` | `accept-dns=false`, `accept-routes=false`, `ssh=false`, no advertised routes |

## Verification

Baseline subnet-router checks:

```sh
ip route get 192.168.20.11
ip route get 192.168.20.12
ssh ubuntu@192.168.20.11 hostname
ssh ubuntu@192.168.20.12 hostname
getent ahostsv4 node-1.lan
getent ahostsv4 node-2.lan
```

After direct worker enrollment:

```sh
tailscale status --json | jq -r '.Peer[] | [.HostName, .DNSName, (.TailscaleIPs | join(",")), .Online] | @tsv'
ssh ubuntu@node-1.shark-garibaldi.ts.net hostname
ssh ubuntu@node-2.shark-garibaldi.ts.net hostname
```

Expected state:

- Tailscale admin Machines includes `node-0`, `node-1`, and `node-2`.
- OpenWrt advertises only `192.168.20.0/24`.
- `node-1` and `node-2` do not advertise routes.
- `node-1.lan` and `node-2.lan` resolve through split DNS.
- SSH works by LAN IP through the subnet router and by Tailscale DNS name after
  direct enrollment.
