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

# LAN ingress hairpin

OpenWrt answers `*.soyspray.vip` with its Tailscale address `100.96.77.28` and
forwards ports 80 and 443 to the ingress VIP `192.168.20.20`. A device on the
LAN without Tailscale, such as the living-room TV, reaches that forward from
the LAN side. `set-lan-ingress-hairpin.yml` adds the matching source NAT, so
the ingress replies through the router instead of straight to the device, which
would otherwise drop the reply and time out.

```bash
source soyspray-venv/bin/activate
ansible-playbook playbooks/operations/networking/set-lan-ingress-hairpin.yml
```

The run is safe to repeat and reloads the firewall only when it adds the rule.
Check it from a LAN-only device, for example the TV's Jellyfin client reaching
`https://tv.soyspray.vip`; a Tailscale client such as the laptop always uses the
Tailscale path and drops replies from Tailscale addresses on its LAN interface.
Remove it with `uci delete firewall.soyspray_lan_hairpin && uci commit firewall
&& fw4 reload` on the router.
