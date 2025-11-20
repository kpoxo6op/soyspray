# OpenWrt DNS & Remote Access Migration Plan 2

## Overview

Transfer DNS authority for `soyspray.vip` from Pi‑hole (k8s) to OpenWrt and use
Tailscale for remote access with **subnet routing + split‑DNS**. This removes
the cluster as a dependency for LAN name resolution and delivers the same
hostnames on LAN and remotely.

## Pre‑Migration State

* Router: **OpenWrt 24.10.0** at **192.168.1.1** with DHCP scope **192.168.1.100–192.168.1.249** (`start=100`, `limit=150`)
* K8s Node: **node-0** at **192.168.1.10**
* MetalLB Primary Pool: **192.168.1.20–192.168.1.38** (outside router DHCP range)
* MetalLB Torrent Pool: **192.168.1.39**
* Current DNS: **Pi‑hole in k8s**
* Target Domain: **soyspray.vip**
* Repo context for services/apps: ArgoCD apps live under
  `playbooks/argocd/applications/`.
* Root repo layout reference lives alongside playbooks and Kubespray.

---

## The One Pitfall (read first)

Binding dnsmasq to `tailscale0` while keeping `nonwildcard='1'` removes DHCP/DNS
from LAN and leaves Wi‑Fi SSIDs up but unusable. Keep dnsmasq on all interfaces
and avoid interface pinning.

---

## Step 1 — Make OpenWrt authoritative for `soyspray.vip`

Wildcard A for `*.soyspray.vip → 192.168.1.20`

```bash
ssh root@192.168.1.1 '
uci add_list dhcp.@dnsmasq[0].address="/soyspray.vip/192.168.1.20"
uci add_list dhcp.@dnsmasq[0].rebind_domain="soyspray.vip"
uci set dhcp.@dnsmasq[0].local_ttl="30"

uci -q delete dhcp.@dnsmasq[0].interface
uci set dhcp.@dnsmasq[0].nonwildcard="0"

uci add_list dhcp.@dnsmasq[0].server="1.1.1.1"
uci add_list dhcp.@dnsmasq[0].server="8.8.8.8"

uci commit dhcp
/etc/init.d/dnsmasq restart
'
```

**Verify**

```bash
ssh root@192.168.1.1 'nslookup soyspray.vip 127.0.0.1'
ssh root@192.168.1.1 'nslookup torrent.soyspray.vip 127.0.0.1'
nslookup radarr.soyspray.vip 192.168.1.1
```

---

## Step 2 — Install Tailscale on OpenWrt

```bash
ssh root@192.168.1.1 '
opkg update
opkg install tailscale
/etc/init.d/tailscaled enable
/etc/init.d/tailscaled start
'
```

**Verify**

```bash
ssh root@192.168.1.1 '/etc/init.d/tailscaled status'
ssh root@192.168.1.1 'tailscale version'
```

---

## Step 3 — Firewall: Tailscale zone with LAN access (fw4)

```bash
ssh root@192.168.1.1 '
uci add firewall zone
uci set firewall.@zone[-1].name="tailscale"
uci set firewall.@zone[-1].input="ACCEPT"
uci set firewall.@zone[-1].forward="ACCEPT"
uci set firewall.@zone[-1].output="ACCEPT"
uci add_list firewall.@zone[-1].device="tailscale0"

uci add firewall forwarding
uci set firewall.@forwarding[-1].src="tailscale"
uci set firewall.@forwarding[-1].dest="lan"

uci commit firewall
/etc/init.d/firewall restart
'
```

**Verify**

```bash
ssh root@192.168.1.1 'fw4 print | grep -n tailscale'
```

---

## Step 4 — Subnet router configuration (no exit node)

```bash
ssh root@192.168.1.1 '
tailscale up --accept-dns=false --accept-routes=true \
  --advertise-routes=192.168.1.0/24 \
  --ssh
'
```

**Verify**

```bash
ssh root@192.168.1.1 'tailscale status'
ssh root@192.168.1.1 'tailscale ip -4'
ssh root@192.168.1.1 'ip link show tailscale0'
```

---

## Step 5 — Approve the subnet route in Tailscale admin

**Clicks:** Machines → OpenWrt router → Edit route settings → Enable
**192.168.1.0/24** → Save.

**Verify from a tailnet device**

```bash
curl -I http://192.168.1.21
```

---

## Step 6 — Split DNS (minimal, correct)

**Design:** Use MagicDNS and global resolvers for public DNS. Route
`soyspray.vip` to OpenWrt over the subnet route.

**Admin console**

1. DNS → **Enable MagicDNS**.
2. Global nameservers → **Override** → add **1.1.1.1** and **8.8.8.8** → Save.
3. Split DNS → Domain: `soyspray.vip` → Nameserver: `192.168.1.1` → Save.

**Router (allow Tailscale queries to dnsmasq)**

```bash
ssh root@192.168.1.1 '
uci set dhcp.@dnsmasq[0].localservice="0"
uci commit dhcp
/etc/init.d/dnsmasq restart
'
```

**Quick test (tailnet device)**

* Browse to `http://radarr.soyspray.vip` and `http://torrent.soyspray.vip`.

---

## Step 7 — Guardrail: never bind dnsmasq to `tailscale0`

**Rule:** Keep dnsmasq unpinned and wide‑listening. Enforce **`nonwildcard=0`**,
**no `list interface` lines**, and **`localservice=0`**.

**Enforce + verify**

```bash
ssh root@192.168.1.1 '
uci -q delete dhcp.@dnsmasq[0].interface
uci set dhcp.@dnsmasq[0].nonwildcard="0"
uci set dhcp.@dnsmasq[0].localservice="0"
uci commit dhcp
/etc/init.d/dnsmasq restart

uci get dhcp.@dnsmasq[0].nonwildcard
uci get dhcp.@dnsmasq[0].localservice
uci show dhcp.@dnsmasq[0] | grep -E "^\s*list interface" || true
ss -lun | grep ":53 "
'
```

**Expected:** `nonwildcard=0`, `localservice=0`, no `list interface` lines,
listeners on `0.0.0.0:53` and `[::]:53`.

---

## End‑to‑End tests

**Remote over Tailscale**

```bash
nslookup radarr.soyspray.vip 100.100.100.100
curl -I http://radarr.soyspray.vip
```

**LAN**

```bash
nslookup radarr.soyspray.vip 192.168.1.1
curl -I http://radarr.soyspray.vip
```
