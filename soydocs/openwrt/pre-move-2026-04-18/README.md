# OpenWrt Pre-Move Snapshot

Captured from the live router over SSH on `2026-04-18` before moving to a new
upstream network.

This snapshot is intentionally sanitized before committing:

- Wi-Fi PSK removed
- MAC addresses removed
- Public WAN IP and default gateway removed
- Tailscale IPs removed

The local raw backup archive remains outside git in `.router-backups/` and is
not safe to commit because it may contain secrets.

## Current topology summary

- OpenWrt LAN gateway: `192.168.1.1/24`
- LAN bridge: `br-lan` on `eth1`
- WAN uplink: DHCP on VLAN `eth0.10`
- Primary Wi-Fi SSID: `123AAotea` on 2.4 GHz
- 5 GHz radio: configured but disabled
- Local DNS override: `soyspray.vip -> 192.168.1.20`
- Static DHCP reservations:
  - `node-0 -> 192.168.1.10`
  - `mox -> 192.168.1.50`
- Tailscale enabled with a dedicated firewall zone forwarding to LAN
- Syslog forwarded to `192.168.1.10:514/udp`

## Migration relevance

The values most likely to change after the house move are:

- LAN subnet, if the new upstream router also uses `192.168.1.0/24`
- WAN addressing mode and upstream details
- `soyspray.vip` local override target, if service IPs move
- Tailscale subnet advertisement, if the LAN subnet changes

The values most likely to stay useful are:

- VLAN uplink requirement on `eth0.10`
- DHCP reservation intent for `node-0` and `mox`
- Firewall structure including the `tailscale` zone
- Wi-Fi SSID and radio settings
