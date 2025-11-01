# OpenWrt DNS & Remote Access Migration Plan

FAILED

## Overview
Migrate DNS authority from Pi-hole (k8s) to OpenWrt router and configure Tailscale for remote access. This eliminates DNS dependency on cluster availability.

## Pre-Migration State
- Router: OpenWrt 24.10.0 at 192.168.1.1
- K8s Node: node-0 at 192.168.1.10
- MetalLB Primary Pool: 192.168.1.20-192.168.1.38
- MetalLB Torrent Pool: 192.168.1.39
- Current DNS: Pi-hole in k8s (creates SPOF)
- Target Domain: soyspray.vip

## Step 1: Configure OpenWrt DNS for soyspray.vip ✅

### What This Does

This step makes the router the DNS authority for all soyspray.vip hostnames. Instead of managing individual DNS records for each service (radarr.soyspray.vip, sonarr.soyspray.vip, etc.), this uses a wildcard pattern that automatically resolves ANY subdomain to the MetalLB ingress IP.

How it works:
1. `/soyspray.vip/192.168.1.20` - Tells dnsmasq: "Any request for soyspray.vip or *.soyspray.vip returns 192.168.1.20"
2. `/torrent.soyspray.vip/192.168.1.39` - Overrides the wildcard for torrent specifically (dedicated IP pool)
3. `rebind_domain="soyspray.vip"` - Allows the router to return private IPs for this domain (security whitelist)
4. `local_ttl="30"` - DNS responses expire in 30 seconds (allows faster updates when testing)

Result: Any device on the LAN asking for radarr.soyspray.vip, plex.soyspray.vip, or newapp.soyspray.vip gets 192.168.1.20 automatically. No per-app DNS configuration needed. The router DNS works even when the k8s cluster is down.

### Actions
```bash
ssh root@192.168.1.1 '
uci add_list dhcp.@dnsmasq[0].address="/soyspray.vip/192.168.1.20"
uci add_list dhcp.@dnsmasq[0].address="/torrent.soyspray.vip/192.168.1.39"
uci add_list dhcp.@dnsmasq[0].rebind_domain="soyspray.vip"
uci set dhcp.@dnsmasq[0].local_ttl="30"
uci commit dhcp
/etc/init.d/dnsmasq restart
'
```

### Verification
```bash
# Test wildcard resolution
ssh root@192.168.1.1 'nslookup soyspray.vip 127.0.0.1'
# Expected: 192.168.1.20

ssh root@192.168.1.1 'nslookup app.soyspray.vip 127.0.0.1'
# Expected: 192.168.1.20

ssh root@192.168.1.1 'nslookup torrent.soyspray.vip 127.0.0.1'
# Expected: 192.168.1.39

# Test from local machine
nslookup radarr.soyspray.vip 192.168.1.1
# Expected: 192.168.1.20
```

## Step 2: Install Tailscale on OpenWrt ✅

### Actions
```bash
ssh root@192.168.1.1 '
opkg update
opkg install tailscale
/etc/init.d/tailscaled enable
/etc/init.d/tailscaled start
'
```

### Verification
```bash
ssh root@192.168.1.1 '/etc/init.d/tailscaled status'
# Expected: running

ssh root@192.168.1.1 'tailscale version'
# Expected: version number displayed
```

## Step 3: Configure Tailscale Firewall Zone ✅

### What This Does

This step creates firewall rules that allow Tailscale traffic to flow between the tailnet and the LAN. Without this, devices on the tailnet cannot access anything on the LAN subnet.

How it works:
1. `uci add firewall zone` - Creates a new firewall zone named "tailscale"
2. `input/forward/output="ACCEPT"` - Allows all traffic in/through/out of the Tailscale zone
3. `device="tailscale0"` - Binds the zone to the tailscale0 network interface
4. `uci add firewall forwarding` - Creates a forwarding rule from tailscale zone to lan zone
5. `src="tailscale" dest="lan"` - Allows traffic from tailnet to reach LAN devices

Result: When connected to the tailnet remotely, devices can reach the entire 192.168.1.0/24 LAN subnet, including the k8s node at 192.168.1.10 and all services behind MetalLB IPs. The firewall permits but secures this access through Tailscale's authentication.

### Actions
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

### Verification
```bash
ssh root@192.168.1.1 'uci show firewall | grep tailscale'
# Expected: zone and forwarding rules displayed

ssh root@192.168.1.1 'iptables -L -n | grep -A 5 "Chain zone_tailscale"'
# Expected: chain rules visible
```

## Step 4: Authenticate Tailscale with Subnet Routing ✅

### What This Does

This step authenticates the router with the Tailscale network and advertises the LAN subnet so remote devices can access it.

How it works:
1. `--accept-dns=false` - Don't let Tailscale override router's DNS settings (router controls DNS)
2. `--accept-routes=true` - Accept subnet routes advertised by other devices on tailnet
3. `--advertise-routes=192.168.1.0/24` - Tell tailnet that this router can provide access to LAN subnet
4. `--advertise-exit-node=true` - Offer this router as an exit node (optional VPN gateway)
5. `--ssh` - Enable Tailscale SSH for secure remote router access

Result: Router is authenticated to the tailnet with IP 100.91.194.113. The router advertises the 192.168.1.0/24 subnet (must be approved in Tailscale admin console in Step 5). Remote devices can now see the router on the tailnet.

### Actions
```bash
ssh root@192.168.1.1 '
tailscale up --accept-dns=false --accept-routes=true \
  --advertise-routes=192.168.1.0/24 \
  --advertise-exit-node=true \
  --ssh
'
```

### Verification
```bash
ssh root@192.168.1.1 'tailscale status'
# Expected: router listed with status, subnet routes advertised

ssh root@192.168.1.1 'tailscale ip -4'
# Expected: 100.x.y.z IP address

ssh root@192.168.1.1 'ip link show tailscale0'
# Expected: interface exists and UP
```

## Step 5: Enable Subnet Routes in Tailscale Admin Console ✅

### What This Does

This step approves the subnet route advertised by the router in Step 4. Until approved, other devices on the tailnet cannot access the LAN subnet through the router.

How it works:
1. Router advertises 192.168.1.0/24 as available route
2. Admin console shows it as "Awaiting Approval" for security
3. Administrator reviews and approves the subnet route
4. Tailscale network updates routing tables across all devices
5. Remote devices can now reach 192.168.1.0/24 through the router's 100.91.194.113 IP

Result: Subnet route 192.168.1.0/24 is now approved and active. Any device on the tailnet can access the entire LAN network (including 192.168.1.10 k8s node and 192.168.1.20 MetalLB IPs) when connected to Tailscale.

### Actions
1. Open Tailscale admin console in browser
2. Navigate to Machines
3. Find OpenWrt router entry
4. Click three-dot menu
5. Select "Edit route settings"
6. Enable subnet route: 192.168.1.0/24
7. Save changes

### Verification
```bash
# From remote device (not on LAN) with Tailscale enabled
ping 192.168.1.1
# Expected: replies from router

ping 192.168.1.10
# Expected: replies from k8s node
```

Verified from Google Pixel 9 Pro XL via Tailscale:
- ping 192.168.1.1: 4 packets transmitted, 4 received, 0% packet loss
- Round-trip times: min 10.988ms / avg 23.092ms / max 43.290ms
- Subnet route working correctly ✅

## Step 6: Configure Tailscale Split DNS ✅ (REQUIRES FIX - SEE BELOW)

### What This Does

This step configures Tailscale to send all DNS queries for soyspray.vip to the router's dnsmasq server via the tailnet. This makes the same DNS configuration work both on LAN and remotely.

How it works:
1. MagicDNS enables Tailscale's built-in DNS resolver (100.100.100.100)
2. Split DNS routes queries for specific domains to specific nameservers
3. soyspray.vip queries are sent to 100.91.194.113 (router's tailnet IP)
4. Router's dnsmasq resolves *.soyspray.vip to 192.168.1.20 (configured in Step 1)
5. Tailscale devices can reach 192.168.1.20 via subnet route (configured in Step 5)

Result: When connected to Tailscale remotely, queries for radarr.soyspray.vip resolve to 192.168.1.20 via the router, then traffic routes through the subnet to reach the actual service. Same DNS works on LAN and remotely.

### Actions
1. Open Tailscale admin console
2. Navigate to DNS settings
3. Enable MagicDNS
4. Configure Global nameservers (CRITICAL - see warning below):
   - Scroll to "Global nameservers" section
   - Enable "Override DNS servers"
   - Add nameservers:
     - 1.1.1.1 (Cloudflare)
     - 8.8.8.8 (Google)
   - Save
5. Add Split DNS entry:
   - Domain: `soyspray.vip`
   - Nameserver: `100.91.194.113` (router's tailnet IP from Step 4)
6. Save changes

### CRITICAL WARNING - MagicDNS Requires Global Nameservers

When MagicDNS is enabled, it becomes the ONLY DNS resolver for all Tailscale devices. Without Global nameservers configured, ALL internet DNS queries will fail.

What happened during initial implementation:
- MagicDNS enabled without Global nameservers
- Split DNS configured only for soyspray.vip
- Result: Tailscale devices could not resolve ANY other domains (google.com, etc.)
- Both laptop and phone lost internet connectivity
- Phone's cellular data also broke because Tailscale overrode system DNS
- Only Tailscale IP-to-IP communication worked (e.g., SSH to 192.168.1.1)

Root cause:
- MagicDNS (100.100.100.100) had no upstream nameservers
- Only soyspray.vip was routed to router (100.91.194.113)
- All other DNS queries had nowhere to go

The fix:
- Add Global nameservers (1.1.1.1, 8.8.8.8) in Tailscale admin console
- These handle all non-soyspray.vip queries
- Split DNS only handles soyspray.vip queries to router

### Verification
```bash
# From remote device (not on LAN) with Tailscale enabled

# Test internet DNS works (via Global nameservers)
nslookup google.com
# Expected: resolves to Google IPs

# Test soyspray.vip DNS works (via Split DNS to router)
nslookup soyspray.vip
# Expected: 192.168.1.20

nslookup radarr.soyspray.vip
# Expected: 192.168.1.20

nslookup torrent.soyspray.vip
# Expected: 192.168.1.39
```

## Step 6.1: Fix MagicDNS Configuration (REQUIRED BEFORE ROUTER RESTART)

This step must be completed BEFORE plugging the OpenWrt router back in to prevent internet connectivity loss.

### Actions
1. Open browser and navigate to Tailscale admin console: https://login.tailscale.com/admin/dns
2. Scroll to "Nameservers" section
3. Find "Global nameservers" subsection
4. Click the toggle or checkbox to enable "Override DNS servers"
5. Click "Add nameserver" button
6. Enter: 1.1.1.1
7. Click "Add nameserver" button again
8. Enter: 8.8.8.8
9. Click "Save" or ensure changes are committed
10. Verify the configuration shows:
    - Global nameservers: 1.1.1.1, 8.8.8.8
    - Split DNS: soyspray.vip → 100.91.194.113

### Verification Before Router Reconnection
From laptop (still on eero network):
```bash
# Check current DNS configuration
cat /etc/resolv.conf
# Should show: nameserver 100.100.100.100

# Test internet DNS
nslookup google.com
# Expected: resolves correctly via 1.1.1.1 or 8.8.8.8

# Test split DNS (will fail until router back online)
nslookup soyspray.vip
# Expected: May fail or timeout (router offline), but google.com should work
```

### Will Router Work When Plugged Back In?

YES, the OpenWrt router will work correctly when reconnected because:

1. All Tailscale configuration is stored in Tailscale's cloud
   - Global nameservers (1.1.1.1, 8.8.8.8) are configured in Tailscale admin
   - Split DNS for soyspray.vip is configured in Tailscale admin
   - Subnet routes are approved in Tailscale admin

2. Router's local configuration is preserved in OpenWrt's UCI config:
   - dnsmasq wildcard DNS for soyspray.vip → 192.168.1.20
   - dnsmasq listening on tailscale0 interface
   - Tailscale daemon configured with subnet routing
   - Firewall rules for Tailscale zone

3. When router powers on:
   - Tailscale daemon starts automatically
   - Connects to tailnet with existing configuration
   - dnsmasq starts and listens on LAN + tailscale0
   - Firewall rules load automatically

4. Devices will work immediately:
   - LAN devices use router's dnsmasq directly (192.168.1.1)
   - Tailscale devices use MagicDNS (100.100.100.100) which forwards:
     - Internet queries → 1.1.1.1 / 8.8.8.8
     - soyspray.vip queries → 100.91.194.113 (router via tailnet)

The only change needed is adding Global nameservers in Tailscale admin console (Step 6.1 above).

## Step 7: Update dnsmasq to Listen on Tailscale Interface ✅

### What This Does

This step configures dnsmasq to accept DNS queries on the Tailscale interface. By default, dnsmasq only listens on the LAN interface. Adding tailscale0 allows remote devices to query DNS through the tailnet.

How it works:
1. `uci add_list` adds tailscale0 to the list of interfaces dnsmasq listens on
2. dnsmasq restarts and binds to the router's tailnet IP (100.91.194.113)
3. Remote devices can now query DNS at 100.91.194.113:53 over the tailnet
4. Split DNS in Tailscale (Step 6) sends soyspray.vip queries to this IP

Result: dnsmasq is listening on 100.91.194.113:53, ready to resolve soyspray.vip queries from remote Tailscale devices.

### Actions
```bash
ssh root@192.168.1.1 '
uci add_list dhcp.@dnsmasq[0].interface="tailscale0"
uci commit dhcp
/etc/init.d/dnsmasq restart
'
```

### Verification
```bash
ssh root@192.168.1.1 'netstat -uln | grep :53'
# Expected: listening on tailscale0 IP

# From remote device
nslookup app.soyspray.vip
# Expected: 192.168.1.20 resolved via tailnet
```

Verified:
- dnsmasq listening on 100.91.194.113:53 (tailscale0 interface) ✅
- Also listening on 127.0.0.1:53 and IPv6 addresses ✅
- Ready to serve DNS queries from remote Tailscale devices ✅

## Step 7.1: Fix Internet Connectivity Issue (REQUIRED)

After Step 7, the router WiFi SSID broadcasts but devices have no internet.

### Problem

The command `uci add_list dhcp.@dnsmasq[0].interface="tailscale0"` may have restricted dnsmasq to ONLY listen on tailscale0, or caused dnsmasq to fail if tailscale0 doesn't exist yet.

### Fix Option A: Remove tailscale0 interface restriction (Recommended)

```bash
ssh root@192.168.1.1 '
# Remove the tailscale0 interface restriction
uci del_list dhcp.@dnsmasq[0].interface="tailscale0"

# Add upstream DNS servers (important!)
uci add_list dhcp.@dnsmasq[0].server="1.1.1.1"
uci add_list dhcp.@dnsmasq[0].server="8.8.8.8"

uci commit dhcp
/etc/init.d/dnsmasq restart
'
```

This makes dnsmasq listen on ALL interfaces (default behavior) including tailscale0 when it comes up.

### Fix Option B: Explicitly configure interfaces

```bash
ssh root@192.168.1.1 '
# Check current interface config
uci show dhcp.@dnsmasq[0] | grep interface

# If broken, reset to proper config
uci delete dhcp.@dnsmasq[0].interface
uci add_list dhcp.@dnsmasq[0].interface="lan"
uci add_list dhcp.@dnsmasq[0].interface="loopback"

# Add upstream DNS servers
uci add_list dhcp.@dnsmasq[0].server="1.1.1.1"
uci add_list dhcp.@dnsmasq[0].server="8.8.8.8"

uci commit dhcp
/etc/init.d/dnsmasq restart
'
```

### Verification

```bash
# Test router can resolve internet domains
ssh root@192.168.1.1 'nslookup google.com'
# Expected: resolves successfully

# Test router can reach internet by IP
ssh root@192.168.1.1 'ping -c 3 8.8.8.8'
# Expected: replies

# From device on WiFi
nslookup google.com
# Expected: resolves via 192.168.1.1

ping 8.8.8.8
# Expected: internet works
```

### Note on Tailscale DNS

Once internet is working, Tailscale devices will still query the router via its tailnet IP (100.91.194.113) because:
- dnsmasq listens on ALL interfaces by default
- Tailscale's netfilter/routing will direct queries to 100.91.194.113:53
- This works even without explicit `interface="tailscale0"` configuration

## Step 7.2: Complete Rollback (If Needed)

If the router is completely broken and needs a full rollback to working state, follow these steps.

### What This Does

This removes ALL changes from the migration and restores the router to its pre-migration working state. Use this only if Step 7.1 doesn't fix the issue.

### Rollback Actions

```bash
ssh root@192.168.1.1 '
# 1. Remove soyspray.vip DNS records (Step 1)
uci del_list dhcp.@dnsmasq[0].address="/soyspray.vip/192.168.1.20"
uci del_list dhcp.@dnsmasq[0].address="/torrent.soyspray.vip/192.168.1.39"
uci del_list dhcp.@dnsmasq[0].rebind_domain="soyspray.vip"
uci delete dhcp.@dnsmasq[0].local_ttl

# 2. Remove tailscale0 interface from dnsmasq (Step 7)
uci del_list dhcp.@dnsmasq[0].interface="tailscale0"

# 3. Ensure upstream DNS servers are configured
uci add_list dhcp.@dnsmasq[0].server="1.1.1.1"
uci add_list dhcp.@dnsmasq[0].server="8.8.8.8"

# Commit dnsmasq changes
uci commit dhcp
/etc/init.d/dnsmasq restart

# 4. Remove Tailscale firewall zone (Step 3)
uci delete firewall.@zone[-1]
uci delete firewall.@forwarding[-1]
uci commit firewall
/etc/init.d/firewall restart

# 5. Stop and disable Tailscale (Step 2)
/etc/init.d/tailscale stop
/etc/init.d/tailscale disable
'
```

### Optional: Completely Remove Tailscale

```bash
ssh root@192.168.1.1 '
opkg remove tailscale
'
```

### Verification After Rollback

```bash
# Test basic connectivity
ssh root@192.168.1.1 'nslookup google.com'
# Expected: resolves

ssh root@192.168.1.1 'ping -c 3 8.8.8.8'
# Expected: internet works

# From device on OpenWrt WiFi
nslookup google.com
ping google.com
# Expected: both work

# Check Tailscale is stopped
ssh root@192.168.1.1 'tailscale status'
# Expected: error or offline
```

### What You Lose in Rollback

After complete rollback:
- No local DNS for soyspray.vip (back to Pi-hole dependency)
- No Tailscale remote access via router
- No subnet routing (192.168.1.0/24 not accessible remotely)
- But: Router works normally for LAN internet access

### Tailscale Client Configuration Remains

Note: Tailscale admin console still has:
- MagicDNS enabled
- Global nameservers (1.1.1.1, 8.8.8.8)
- Split DNS for soyspray.vip → 100.91.194.113

Your laptop/phone Tailscale will continue to work with these settings, but:
- soyspray.vip queries will timeout (router offline on tailnet)
- Internet DNS still works via Global nameservers
- You can disable MagicDNS in Tailscale admin if not needed

## Step 8: Test End-to-End Connectivity

### Actions (from remote device with Tailscale)
```bash
# Test DNS resolution
nslookup radarr.soyspray.vip

# Test HTTP connectivity (if ingress configured)
curl -I https://radarr.soyspray.vip -k

# Test from LAN device
curl -I https://radarr.soyspray.vip -k
```

### Verification
- DNS resolves correctly on LAN: ✓
- DNS resolves correctly on tailnet: ✓
- HTTP access works on LAN: ✓
- HTTP access works on tailnet: ✓
