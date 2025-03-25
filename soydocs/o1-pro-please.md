# reply

Below is a practical checklist of what usually goes wrong when trying to reach Pi-hole (both web and DNS) across a WireGuard “hub-and-spoke” tunnel—plus how to fix it in a Kubernetes + MetalLB + Pi-hole Helm setup. Follow these steps and you should end up with a working Pi-hole that serves DNS (and the web UI) to your mobile phone over WireGuard.

────────────────────────────────────────────────────────────────────────

1) Confirm Basic TCP/UDP Path
────────────────────────────────────────────────────────────────────────
 • From your mobile phone’s WireGuard client, verify you can still reach other services in the cluster on Metallb-managed IPs (e.g. ArgoCD, Grafana).
   – If these are accessible, your fundamental WireGuard routing is correct.
   – If they fail, double-check “AllowedIPs” in both the server and the home WireGuard configs and confirm that 192.168.1.0/24 is routed to the home node peer.

 • Double-check the Azure VPS’s UFW/iptables settings (or netfilter-persistent):
   – You already have ufw allow in on wg0 from 10.8.0.0/24 to 192.168.1.122 port 53 proto tcp/udp
   – And ufw allow in on wg0 from 10.8.0.0/24 to 192.168.1.122 port 80 proto tcp
   – There is also ufw allow from 10.8.0.0/24 to any which should cover everything else.
   – So from a firewall perspective, it should be open.

 • If you can reach <http://192.168.1.100:3000> or other Argo/Grafana IPs, try a simple ping or curl to 192.168.1.122 over WireGuard:
     ping 192.168.1.122
     curl <http://192.168.1.122/admin>
   If 192.168.1.122 is silent, move on to step (2).

────────────────────────────────────────────────────────────────────────
2) Check Pi-hole’s “Interface Listening Behavior”
────────────────────────────────────────────────────────────────────────
By default, Pi-hole may only “listen” for DNS on the local subnet or may reject queries that appear to come from non-local networks. In a normal Docker or “hostNetwork: false” scenario, Pi-hole sees traffic from the cluster “bridge” (or from MetalLB NAT), and sometimes it does not consider that “local.”

The quickest fix is to ensure Pi-hole is configured to listen on all interfaces and accept requests from any origin. In a standard Pi-hole container, this is done with environment variables such as:

- DNSMASQ_LISTENING=all
- PIHOLE_INTERFACE=eth0

Depending on the Helm chart, you either:
(1) supply these as extraEnv variables, or
(2) set Pi-hole’s “interface listening behavior” from the Admin UI → Settings → DNS → “Interface listening behavior” → choose “Listen on all interfaces, permit all origins.”

Example values stanza snippet (many charts let you pass environment variables)
-------------------------------------------------------------------------------

extraEnv:

- name: DNSMASQ_LISTENING
    value: "all"
- name: PIHOLE_INTERFACE
    value: "eth0"

-------------------------------------------------------------------------------

Make sure that your cluster is not overriding Pi-hole’s default environment by rummaging through the Helm chart’s docs for pihole/pihole.

────────────────────────────────────────────────────────────────────────
3) MetalLB + LoadBalancer Ports
────────────────────────────────────────────────────────────────────────
Your values.yaml shows two LoadBalancer services, both assigning the same IP (192.168.1.122) with metallb.universe.tf/allow-shared-ip. That’s valid, but double-check that you have:

serviceWeb:
  type: LoadBalancer
  loadBalancerIP: 192.168.1.122
  http:
    enabled: true
    port: 80
  …

serviceDns:
  type: LoadBalancer
  loadBalancerIP: 192.168.1.122
  port: 53
  mixedService: true
  …

If other LB-based apps (ArgoCD, Grafana, etc.) work fine, then MetalLB is already handing out ARP for that IP. But confirm that the Pi-hole pods and Services are actually “Ready.” For instance:
   kubectl get svc -n pihole
   kubectl get pods -n pihole -o wide
Make sure there’s no CrashLoop, and that the externalTrafficPolicy setting is consistent (“Cluster” vs. “Local”) with your normal usage. Often “Cluster” mode works fine, but if the Pi-hole container cares about the source IP, “Local” might be required.

────────────────────────────────────────────────────────────────────────
4) Verify Return Traffic from Pi-hole
────────────────────────────────────────────────────────────────────────
Even though traffic arrives at Pi-hole from the mobile phone (over the hub→home node→cluster path), Pi-hole must return the packets the same way. Because your home node’s WireGuard config sets:
  AllowedIPs = 192.168.1.0/24
the home node should route any 192.168.1.x traffic back out over wg0 if the destination is 10.8.0.x. This generally “just works,” and you confirmed other cluster apps can respond. So if Pi-hole alone fails, it often means Pi-hole is ignoring queries from that subnet or not binding to the correct interface.

A quick test is to run a packet capture either on the home WireGuard node or directly in the Pi-hole pod:

• On the home node (assuming Linux):
  sudo tcpdump -ni wg0 host 192.168.1.122 or host 10.8.0.2
• Inside the Pi-hole container:
  kubectl exec -n pihole <pod-name> -- tcpdump -ni any port 53
Check if queries arrive from 10.8.0.x, and if responses are going back out.

────────────────────────────────────────────────────────────────────────
5) Configure Your Phone to Use Pi-hole DNS
────────────────────────────────────────────────────────────────────────
Once you confirm that you can curl <http://192.168.1.122/admin> from your phone over WireGuard, you can then make sure the phone picks up Pi-hole as its DNS:

• In the generated /etc/wireguard/client.conf (on Azure), you already have:
    DNS = 192.168.1.122
• Make sure the WireGuard app on your phone is set to “allow apps to use the VPN DNS” if that’s an option. Some phones do not integrate the VPN-provided DNS if split-tunnel or other local settings are in effect.
• For iOS or Android, double-check that your “Allowed IPs = 0.0.0.0/0” so the phone actually routes DNS queries through the tunnel.

Once the phone is definitely sending DNS queries to 192.168.1.122 over the WireGuard interface—and Pi-hole is set to “listen on all interfaces”—DNS queries should get processed.

────────────────────────────────────────────────────────────────────────
6) Final Code/Config Highlights
────────────────────────────────────────────────────────────────────────
Below are the most important bits to review or add if missing:

A) Pi-hole Helm values (snippet)
-------------------------------------------------------------------------------

extraEnv:

- name: DNSMASQ_LISTENING
    value: "all"
- name: PIHOLE_INTERFACE
    value: "eth0"

serviceWeb:
  type: LoadBalancer
  loadBalancerIP: 192.168.1.122
  annotations:
    metallb.universe.tf/allow-shared-ip: "pihole-svc"
  http:
    enabled: true
    port: 80
  https:
    enabled: false

serviceDns:
  type: LoadBalancer
  loadBalancerIP: 192.168.1.122
  annotations:
    metallb.universe.tf/allow-shared-ip: "pihole-svc"
  port: 53
  mixedService: true
  externalTrafficPolicy: Cluster
-------------------------------------------------------------------------------

(Adjust externalTrafficPolicy to Local, if you suspect Pi-hole is discarding non-local requests.)

B) Ensure the Azure VPS WireGuard server allows inbound DNS from your mobile phone to Pi-hole
-------------------------------------------------------------------------------

ufw allow in on wg0 from 10.8.0.0/24 to 192.168.1.122 port 53 proto tcp
ufw allow in on wg0 from 10.8.0.0/24 to 192.168.1.122 port 53 proto udp
ufw allow in on wg0 from 10.8.0.0/24 to 192.168.1.122 port 80 proto tcp
-------------------------------------------------------------------------------

(Applies to your cloud-init snippet. You already do this, but verify it’s present.)

C) On the Pi-hole admin console, if you can reach it locally, confirm:
   Settings → DNS → Interface listening behavior = Listen on all interfaces, permit all origins

────────────────────────────────────────────────────────────────────────
Summary
────────────────────────────────────────────────────────────────────────

1. Confirm you can reach other cluster IPs via WireGuard—this proves routing/firewall are mostly fine.
2. Force Pi-hole to “listen on all interfaces” (DNSMASQ_LISTENING=all). By default, Pi-hole may reject queries from non-local subnets if hostNetwork=false.
3. Use tcpdump on the home WireGuard node or in the Pi-hole pod to confirm DNS queries from 10.8.0.x actually arrive and that Pi-hole is responding.
4. Configure your mobile phone’s WireGuard client to use 192.168.1.122 for DNS, ensuring “Allowed IPs = 0.0.0.0/0” or at least “10.8.0.0/24, 192.168.1.0/24,” so DNS queries go over the VPN.

With those steps, you should be able to browse <http://192.168.1.122/admin> from the phone and use Pi-hole as your encrypted DNS server across the WireGuard tunnel.
