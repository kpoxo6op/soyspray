# 2026-06-29 Two Node Intake

## Summary

Two new Lenovo mini PCs were moved from the upstream `192.168.10.0/24` network
onto the OpenWrt-managed soyspray LAN through the switch.

The existing cluster node stayed online during the intake:

- `node-0`: `192.168.20.10`
- SSH returned hostname `node-0`
- `kubectl get nodes -o wide` showed `node-0` as `Ready`

The two new machines were first observed while still running Windows, then
OpenWrt DHCP reservations were added for the planned Kubernetes node IPs.

`node-2` has since booted Ubuntu from the 22.04.5 autoinstall USB and is
reachable on its reserved address. SSH key access works after replacing the
stale local `known_hosts` entry for `192.168.20.12`.

## Observed Devices

Initial temporary DHCP leases:

| Planned node | MAC | Temporary DHCP lease | Hostname seen |
| --- | --- | --- | --- |
| `node-1` | `98:fa:9b:17:f0:50` | `192.168.20.240` | `*` |
| `node-2` | `98:fa:9b:17:f1:1b` | `192.168.20.236` | `DESKTOP-N7J6OTJ` |

Both MACs were visible on the OpenWrt bridge as wired clients on `br-lan`.
Both machines responded like Windows hosts: ICMP was blocked, and TCP `7680`
was open.

## Stable IP Plan

Pin the new Kubernetes nodes with OpenWrt DHCP reservations:

| Node | MAC | Reserved IP |
| --- | --- | --- |
| `node-1` | `98:fa:9b:17:f0:50` | `192.168.20.11` |
| `node-2` | `98:fa:9b:17:f1:1b` | `192.168.20.12` |

Reasoning:

- Existing cluster node is `node-0` at `192.168.20.10`.
- OpenWrt DHCP pool is `192.168.20.100-192.168.20.249`.
- MetalLB service range is `192.168.20.20-192.168.20.38`.
- Laptop `mox` is reserved at `192.168.20.50`.
- `192.168.20.11` and `192.168.20.12` sit next to `node-0` and are outside the
  DHCP pool and MetalLB range.

## Verification

OpenWrt ping checks before assigning reservations:

```text
PING 192.168.20.11: 3 packets transmitted, 0 packets received
PING 192.168.20.12: 3 packets transmitted, 0 packets received
```

OpenWrt neighbor state after the checks:

```text
192.168.20.11  FAILED
192.168.20.12  INCOMPLETE
```

That confirms the planned stable addresses were not in active use at the time
of this intake.

## Next Steps

1. Add OpenWrt DHCP reservations for the new MACs:
   - `node-1`: `98:fa:9b:17:f0:50` -> `192.168.20.11`
   - `node-2`: `98:fa:9b:17:f1:1b` -> `192.168.20.12`
2. Reboot the two Windows machines, or force DHCP renew, and verify OpenWrt
   leases move from `.240` and `.236` to `.11` and `.12`.
3. Install Ubuntu on the new nodes.
4. Verify SSH access as `ubuntu` on `192.168.20.11` and `192.168.20.12`.
5. Update `kubespray/inventory/soycluster/hosts.yml` with `node-1` and
   `node-2`.
6. Run the Kubespray scale workflow only after the stable IPs and SSH access
   are confirmed.

Do not add the current temporary DHCP addresses `.240` and `.236` to Kubespray.
Kubernetes nodes need stable addresses.

## OpenWrt Reservations Applied

The planned reservations were applied on OpenWrt and dnsmasq was reloaded:

| Node | MAC | Reserved IP |
| --- | --- | --- |
| `node-1` | `98:fa:9b:17:f0:50` | `192.168.20.11` |
| `node-2` | `98:fa:9b:17:f1:1b` | `192.168.20.12` |

Post-reservation state observed from OpenWrt:

- `node-2` requested `192.168.20.12` as MAC `98:fa:9b:17:f1:1b`.
- OpenWrt ARP showed `192.168.20.12` reachable on `br-lan`.
- TCP port `22` on `192.168.20.12` was open.
- SSH banner: `SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.10`.

This means `node-2` is no longer behaving like the original Windows boot. It
has at least reached an Ubuntu environment with OpenSSH running.

## 2026-06-29 Autoinstall Status

After selecting the automatic Ubuntu installer on `node-2`, the display flashed
and went blank. Network checks showed:

- DHCP moved to the pinned address `192.168.20.12`.
- SSH stayed open across repeated checks.
- OpenWrt logs showed DHCP activity around the install/reboot window.
- A later monitor flash matched fresh DHCP activity at about 19:29 local time.
  SSH returned immediately afterward with banner
  `SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.15`, suggesting first-boot package
  updates and a reboot rather than a crash.
- A one-minute watch after that reboot showed stable ping and SSH on every
  sample.
- Public key auth initially failed because the local SSH `known_hosts` entry was
  stale from the earlier install state.
- After replacing the stale host key entry, SSH key auth worked for both
  `ubuntu` and `root`.
- Password auth failed for `ubuntu` and `root` using `123`, `ubuntu`,
  `password`, `soyspray`, `k8s-node`, and `k8s`.
- The initial autoinstall hostname `node-192-168-20-12` was corrected
  imperatively to `node-2`.
- `/etc/hosts` was corrected from a literal `$NEW_HOSTNAME` entry to
  `127.0.1.1 node-2`.
- A cloud-init override was added on the node:
  `/etc/cloud/cloud.cfg.d/99-soyspray-preserve-hostname.cfg` with
  `preserve_hostname: true`.

The practical state is: the machine is online at the correct stable IP and
administrable over SSH key auth.

Confirmed from `node-2`:

- Hostname: `node-2`
- Operating system: Ubuntu 22.04.5 LTS
- Kernel: `5.15.0-185-generic`
- `cloud-init status --long`: `status: done`
- `systemctl is-system-running`: `running`
- Root filesystem: `/dev/nvme0n1p2`, 233 GiB, 4% used
- Network interface: `eno1` at `192.168.20.12/24`

Next recovery options:

1. Repeat the Ubuntu install for `node-1` and verify SSH key access on
   `192.168.20.11`.
2. Add both nodes to the Kubespray inventory only after `node-1` is also
   reachable on its pinned IP.

## 2026-06-29 Node-1 Install Start

After selecting the automatic Ubuntu installer on `node-1`, the display also
went blank during the early install stage.

OpenWrt confirmed the node started using its pinned lease:

- At about 19:46 local time, OpenWrt sent a DHCPNAK for the old Windows lease
  `192.168.20.240` because a static lease was available.
- OpenWrt then offered and acknowledged `192.168.20.11` for MAC
  `98:fa:9b:17:f0:50` with hostname `node-1`.
- ARP showed `192.168.20.11` reachable on `br-lan`.
- ICMP ping and TCP port `22` were not available yet during the first minute of
  monitoring, which is expected while the installer is still in early stages.

A second autoinstall attempt was started at about 20:13 local time after the
first attempt did not reach SSH. OpenWrt saw a fresh DHCP request and ACK for
`192.168.20.11` at about 20:13 local time. During monitoring, `192.168.20.11`
remained on the static lease but did not expose SSH. By about 20:35 local time,
OpenWrt still had the static lease, but ARP for `192.168.20.11` was
`INCOMPLETE`, ICMP ping failed, and SSH returned `No route to host`.

After rebooting `node-1` without the USB drive, OpenWrt saw fresh DHCP activity
for `192.168.20.11` at about 20:37-20:38 local time. ARP became reachable again,
but ICMP ping still failed and TCP ports `22`, `80`, `443`, and `7680` were
closed. That indicates the machine is on the LAN at layer 2 and receiving the
pinned lease, but it has not booted into the expected installed Ubuntu system
with SSH available.

A follow-up port probe showed TCP `7680` open on `192.168.20.11` while SSH
remained closed. This matches the Windows behavior observed before the Ubuntu
install attempts and indicates `node-1` likely booted back into Windows from the
internal disk.

An attempted Windows interaction check found no usable remote-management
surface: RDP `3389`, SMB `445`, WinRM `5985`/`5986`, and SSH `22` were closed.
A full TCP connect scan found only TCP `7680` open.

A later autoinstall run succeeded. OpenWrt saw fresh DHCP for
`192.168.20.11` at about 20:52 local time. The node rebooted and requested DHCP
again at about 21:01 local time, then came back with Ubuntu SSH:

- SSH banner: `SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.15`.
- Key auth worked for both `ubuntu` and `root` after replacing the stale local
  `known_hosts` entry for `192.168.20.11`.
- `cloud-init status --long`: `status: done`.
- `systemctl is-system-running`: `running`.
- The initial autoinstall hostname `node-192-168-20-11` was corrected
  imperatively to `node-1`.
- `/etc/hosts` was corrected from a literal `$NEW_HOSTNAME` entry to
  `127.0.1.1 node-1`.
- A cloud-init override was added on the node:
  `/etc/cloud/cloud.cfg.d/99-soyspray-preserve-hostname.cfg` with
  `preserve_hostname: true`.

## 2026-06-29 Kubespray Scale Completion

Both new nodes were added to `kubespray/inventory/soycluster/hosts.yml` on the
`upgrade/kubespray-latest` submodule branch and assigned to `kube_node`:

| Node | IP | Role |
| --- | --- | --- |
| `node-1` | `192.168.20.11` | worker |
| `node-2` | `192.168.20.12` | worker |

The inventory parsed with:

```sh
ansible-inventory -i kubespray/inventory/soycluster/hosts.yml --graph
```

SSH and privilege escalation worked for all three hosts:

```sh
source soyspray-venv/bin/activate
ansible -i kubespray/inventory/soycluster/hosts.yml all \
  -m ping --become --become-user=root --user ubuntu
```

The Kubespray add-node flow was run from inside the Kubespray submodule so its
own fact-cache settings were active:

```sh
cd kubespray
source ../soyspray-venv/bin/activate
ANSIBLE_CONFIG=ansible.cfg ansible-playbook \
  -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/facts.yml
ANSIBLE_CONFIG=ansible.cfg ansible-playbook \
  -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  scale.yml --limit=node-1,node-2
```

The first scale attempt reached `kubeadm join` but failed because Kubernetes
bootstrap discovery still advertised the pre-move API endpoint
`https://192.168.1.10:6443`. The live `kubeadm-config` ConfigMap and API server
certificate were already correct for `192.168.20.10`, but the public
`kube-public/cluster-info` ConfigMap still contained the old server URL.

Before retrying, `cluster-info` was backed up to:

```text
/tmp/soyspray-cluster-info-before-20260629T094346Z.yaml
```

Then its kubeconfig `server` value was patched to:

```text
https://192.168.20.10:6443
```

After that, the rerun of `scale.yml --limit=node-1,node-2` completed
successfully:

```text
node-1 : failed=0
node-2 : failed=0
```

Final node state:

```text
node-0  Ready  control-plane,worker  192.168.20.10  Ubuntu 22.04.5 LTS
node-1  Ready  <none>                192.168.20.11  Ubuntu 22.04.5 LTS
node-2  Ready  <none>                192.168.20.12  Ubuntu 22.04.5 LTS
```

Confirmed on `node-1` and `node-2`:

- Hostnames are `node-1` and `node-2`.
- `kubelet` is active.
- `containerd` is active.
- Core node pods are running: `calico-node`, `kube-proxy`, `nginx-proxy`, and
  `nodelocaldns`.
