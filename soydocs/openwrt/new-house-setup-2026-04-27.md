# OpenWrt New-House Setup

## Execution log

This section records what was actually done on `2026-04-27` during the
new-house router setup.

### Starting state

- Laptop was on hotspot for internet.
- Laptop Ethernet was connected directly to the OpenWrt `1G` LAN port.
- Wall/EoP adapter was initially unplugged from OpenWrt.
- OpenWrt was reachable only after adding a temporary laptop host route because
  Tailscale was still routing `192.168.1.0/24` through `tailscale0`.
- Temporary laptop management address used: `192.168.1.2/24` on `enp0s31f6`.
- Temporary route used: `192.168.1.1/32` via `enp0s31f6` in Tailscale table 52.
- Live router version before changes: OpenWrt `25.12.1`, target
  `mediatek/filogic`, arch `aarch64_cortex-a53`.
- Live pre-change LAN: `192.168.1.1/24` on `br-lan`.
- Live pre-change WAN: DHCP on tagged device `eth0.10`.
- Live pre-change DNS override: `soyspray.vip -> 192.168.1.20`.
- Live pre-change reservations:
  - `node-0 -> 192.168.1.10`
  - `mox -> 192.168.1.50`
- Live pre-change syslog target: `192.168.1.10:514/udp`.

### Backup

A raw router backup was saved outside git before changing config:

```sh
.router-backups/openwrt-before-new-house-2026-04-27.tar.gz
```

That archive is not safe to commit because it contains raw `/etc/config` and
Tailscale state.

`.router-backups/` was added to `.gitignore` so raw router backups are not
accidentally committed.

### Changes applied

- Changed OpenWrt LAN from `192.168.1.1/24` to `192.168.20.1/24`.
- Kept the LAN bridge on `br-lan`.
- Changed WAN from old tagged `eth0.10` DHCP to untagged `eth0` DHCP.
- Changed WAN6 from old tagged `eth0.10` DHCPv6 to untagged `eth0` DHCPv6.
- Removed the old `eth0.10` VLAN device from UCI.
- Changed local DNS override from `soyspray.vip -> 192.168.1.20` to
  `soyspray.vip -> 192.168.20.20`.
- Kept dnsmasq wide-listening for LAN and Tailscale DNS:
  - `nonwildcard=0`
  - `localservice=0`
  - no `list interface` pinning
- Changed static DHCP reservations:
  - `node-0`: `192.168.1.10` to `192.168.20.10`
  - `mox`: `192.168.1.50` to `192.168.20.50`
- Changed remote syslog target from `192.168.1.10` to `192.168.20.10`.

The first SSH session dropped during `/etc/init.d/network reload`, leaving the
live interface temporarily answering on old `192.168.1.1` while UCI already
contained `network.lan.ipaddr=192.168.20.1`. The remaining host reservation,
WAN, WAN6, and syslog changes were then completed over `192.168.1.1`, followed
by `/etc/init.d/network restart`.

### Verified state after LAN migration

After the network restart:

- Laptop temporary management address changed to `192.168.20.2/24`.
- OpenWrt answered ping and SSH at `192.168.20.1`.
- `br-lan` had `192.168.20.1/24`.
- UCI LAN config was `network.lan.ipaddr='192.168.20.1'`.
- UCI WAN config was `network.wan.device='eth0'`, `network.wan.proto='dhcp'`.
- UCI WAN6 config was `network.wan6.device='eth0'`,
  `network.wan6.proto='dhcpv6'`.
- UCI DNS override was `/soyspray.vip/192.168.20.20`.
- UCI reservations were `node-0=192.168.20.10` and `mox=192.168.20.50`.
- UCI syslog target was `192.168.20.10`.

### Verified state after plugging wall/EoP into OpenWrt WAN

After the wall/EoP cable was plugged into OpenWrt WAN:

- OpenWrt `eth0` link was up.
- OpenWrt WAN DHCP lease: `192.168.1.2/24` on `eth0`.
- OpenWrt default route: `default via 192.168.1.1 dev eth0`.
- OpenWrt LAN stayed on `192.168.20.1/24` on `br-lan`.
- OpenWrt could ping `1.1.1.1` with `0%` packet loss.
- OpenWrt dnsmasq resolved `github.com`.
- OpenWrt dnsmasq resolved `soyspray.vip` to `192.168.20.20`.

### Laptop moved from temporary management to router DHCP

After WAN verification, the temporary static laptop Ethernet setup was removed:

- Removed temporary Tailscale table 52 host routes for old and new router
  management IPs.
- Flushed manual addresses from laptop Ethernet `enp0s31f6`.
- Reconnected `enp0s31f6` with NetworkManager DHCP.

Result:

- Laptop DHCP lease from OpenWrt: `192.168.20.124/24`.
- Laptop default route preferred OpenWrt LAN:
  `default via 192.168.20.1 dev enp0s31f6`.
- Hotspot remained connected as a lower-priority fallback:
  `default via 10.147.147.130 dev wlp2s0 metric 600`.
- OpenWrt lease table showed laptop MAC `c8:f7:50:4e:05:c6` leased
  `192.168.20.124`.
- Laptop could ping `192.168.20.1`.
- Laptop could ping `1.1.1.1` through OpenWrt.
- Laptop DNS resolved `github.com`.
- Laptop HTTPS to `https://github.com` returned `HTTP/2 200`.
- Laptop route to the owner's router became
  `192.168.1.1 via 192.168.20.1 dev enp0s31f6`.
- Laptop could ping upstream gateway `192.168.1.1` through OpenWrt.
- `tailscale ping openwrt` worked via direct LAN path
  `192.168.20.1:41641`.

### Tailscale route update

The router-side Tailscale advertised route was changed with:

```sh
tailscale up --accept-dns=false --accept-routes=true \
  --advertise-routes=192.168.20.0/24 \
  --ssh
```

Verification:

- `tailscale debug prefs` showed `AdvertiseRoutes: ["192.168.20.0/24"]`.
- `tailscale status --json` still showed the old approved route
  `192.168.1.0/24` in `AllowedIPs` and `PrimaryRoutes`.
- That means the router is requesting the new subnet, but the Tailscale control
  plane still needs the new `192.168.20.0/24` route approved and the old
  `192.168.1.0/24` route removed or disabled.
- Tailscale also reported a health warning about the Sydney relay. The router
  still had WAN internet at the same time, so this was not treated as a WAN
  failure.
- There was no local Tailscale CLI command available to approve or disable
  subnet routes in the control plane from this session.

### Tailscale admin approval completed

After the route was approved in the Tailscale admin console:

- `openwrt` showed approved subnet route `192.168.20.0/24`.
- `openwrt` showed no routes awaiting approval.
- Router-side `tailscale status --json` showed `AllowedIPs` containing
  `192.168.20.0/24`.
- Router-side `tailscale status --json` showed `PrimaryRoutes` containing
  `192.168.20.0/24`.
- Laptop-side `tailscale status --json` also showed `openwrt` with
  `AllowedIPs` and `PrimaryRoutes` set to `192.168.20.0/24`.
- The old `192.168.1.0/24` subnet route was absent from the current route
  approval state.

Because this laptop accepts Tailscale subnet routes, approving
`192.168.20.0/24` initially made the laptop route `192.168.20.1` through
`tailscale0` even while physically attached to the same LAN. A local route was
added to Tailscale table 52 so the laptop uses Ethernet directly while on this
LAN:

```sh
ip route replace 192.168.20.0/24 dev enp0s31f6 src 192.168.20.124 table 52
```

Verification after that:

- `ip route get 192.168.20.1` returned
  `192.168.20.1 dev enp0s31f6 table 52 src 192.168.20.124`.
- `ping 192.168.20.1` from the laptop returned sub-millisecond LAN latency.

### Laptop moved from Ethernet to OpenWrt Wi-Fi

The laptop was moved from wired OpenWrt LAN to OpenWrt Wi-Fi SSID
`123AAotea`.

Before disconnecting Ethernet, Wi-Fi was verified independently:

- NetworkManager showed `wlp2s0` connected to `123AAotea`.
- Laptop Wi-Fi DHCP lease: `192.168.20.50/24`.
- Wi-Fi-only ping to `192.168.20.1` succeeded.
- Wi-Fi-only ping to `1.1.1.1` succeeded.
- Wi-Fi-only HTTPS to `https://github.com` returned `HTTP/2 200`.

Then Ethernet was disconnected from the laptop. Final verified laptop state:

- `enp0s31f6` was `DOWN` / unavailable.
- `wlp2s0` was connected to `123AAotea`.
- Laptop address: `192.168.20.50/24`.
- Default route: `default via 192.168.20.1 dev wlp2s0`.
- Active NetworkManager connections: `123AAotea`, `tailscale0`, `lo`,
  `docker0`.
- Ping to router `192.168.20.1`: `0%` packet loss.
- Ping to `1.1.1.1`: `0%` packet loss.
- HTTPS to `https://github.com`: `HTTP/2 200`.

OpenWrt Wi-Fi evidence:

- DHCP lease table showed laptop Wi-Fi MAC `a8:6d:aa:07:93:1f` leased
  `192.168.20.50` with hostname `mox`.
- `iw dev phy0-ap0 station dump` showed the laptop associated on `123AAotea`.
- Router WAN route stayed `default via 192.168.1.1 dev eth0`.
- Router local DNS still resolved `soyspray.vip` to `192.168.20.20`.

Remaining follow-up:

- Update cluster inventory and MetalLB/static service IPs from `192.168.1.x` to
  `192.168.20.x` before bringing cluster services back behind this router.

Current observed uplink from the powerline adapter on the laptop:

- Laptop wired address: `192.168.1.124/24`
- Upstream gateway/DNS: `192.168.1.1`
- Internet works through that gateway
- Upstream does not answer ping, HTTP, or SSH from the laptop

## Required topology change

The old OpenWrt LAN was also `192.168.1.1/24`, so it must not keep that subnet
when its WAN is connected to the owner's router. Use a distinct soyspray LAN:

- OpenWrt LAN gateway: `192.168.20.1/24`
- DHCP pool: `192.168.20.100-192.168.20.249`
- `node-0`: `192.168.20.10`
- MetalLB primary VIP: `192.168.20.20`
- `mox`: `192.168.20.50`
- `soyspray.vip`: `192.168.20.20`
- Tailscale advertised route: `192.168.20.0/24`

## Safe order

1. Connect laptop directly to an OpenWrt LAN port, not through the powerline
   adapter.
2. SSH to the router on the old LAN address: `ssh -F /dev/null root@192.168.1.1`.
3. Change LAN subnet, DNS override, DHCP reservations, and syslog target.
4. Change WAN from old tagged `eth0.10` DHCP to untagged WAN DHCP for the
   powerline/owner-router handoff.
5. Reboot or reload network.
6. Reconnect laptop to OpenWrt LAN/Wi-Fi and verify it gets `192.168.20.x`.
7. Plug OpenWrt WAN into the powerline adapter.
8. Verify OpenWrt gets a WAN lease from the owner router and has internet.
9. Update cluster inventory/MetalLB manifests for `192.168.20.0/24` before
   bringing the cluster back behind the router.

## Router commands

Run from a direct laptop-to-OpenWrt LAN connection:

```sh
ssh -F /dev/null root@192.168.1.1
```

Then on OpenWrt:

```sh
uci set network.lan.ipaddr='192.168.20.1'
uci set network.lan.netmask='255.255.255.0'

uci set dhcp.lan.start='100'
uci set dhcp.lan.limit='150'
uci -q delete dhcp.@dnsmasq[0].address
uci add_list dhcp.@dnsmasq[0].address='/soyspray.vip/192.168.20.20'
uci -q delete dhcp.@dnsmasq[0].interface
uci set dhcp.@dnsmasq[0].nonwildcard='0'
uci set dhcp.@dnsmasq[0].localservice='0'

uci set dhcp.@host[0].ip='192.168.20.10'
uci set dhcp.@host[1].ip='192.168.20.50'

uci set system.@system[0].log_ip='192.168.20.10'

uci set network.wan.device='eth0'
uci set network.wan.proto='dhcp'
uci set network.wan6.device='eth0'
uci set network.wan6.proto='dhcpv6'
uci set network.wan6.reqaddress='try'
uci set network.wan6.reqprefix='auto'

uci commit network
uci commit dhcp
uci commit system

reboot
```

After reconnecting to OpenWrt on the new LAN:

```sh
ssh -F /dev/null root@192.168.20.1 '
ip -4 addr show
ip route
nslookup soyspray.vip 127.0.0.1
'
```

After the WAN is in the powerline adapter and internet works from OpenWrt:

```sh
ssh -F /dev/null root@192.168.20.1 '
tailscale up --accept-dns=false --accept-routes=true \
  --advertise-routes=192.168.20.0/24 \
  --ssh
tailscale status --json | head
'
```
