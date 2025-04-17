#!/bin/bash

# Usage: sudo ./switch-dns.sh [PIHOLE_IP]
# Default Pi-hole IP
PIHOLE_IP="${1:-192.168.1.122}"

# Get all active interfaces managed by NetworkManager
ACTIVE_IFACES=$(nmcli -t -f DEVICE,STATE d | awk -F: '$2=="connected"{print $1}')

# Check current DNS for the first active interface
CURRENT_DNS=$(nmcli device show "$ACTIVE_IFACES" | grep 'IP4.DNS' | awk '{print $2}' | head -n1)

if [[ "$CURRENT_DNS" == "$PIHOLE_IP" ]]; then
    echo "Current DNS is Pi-hole ($PIHOLE_IP). Switching to automatic (DHCP)..."
    for IFACE in $ACTIVE_IFACES; do
        # Get the actual connection name for this interface
        CONN_NAME=$(nmcli -t -f NAME,DEVICE c show --active | grep ":$IFACE$" | cut -d: -f1)
        if [ -n "$CONN_NAME" ]; then
            echo "Modifying connection: $CONN_NAME (device: $IFACE)"
            nmcli connection modify "$CONN_NAME" ipv4.ignore-auto-dns no
            nmcli connection modify "$CONN_NAME" ipv4.dns ""
            nmcli connection up "$CONN_NAME"
        else
            echo "Warning: No active connection found for device $IFACE"
        fi
    done
    echo "DNS reset to automatic (DHCP) for all active interfaces."
else
    echo "Current DNS is $CURRENT_DNS. Switching to Pi-hole ($PIHOLE_IP)..."
    for IFACE in $ACTIVE_IFACES; do
        # Get the actual connection name for this interface
        CONN_NAME=$(nmcli -t -f NAME,DEVICE c show --active | grep ":$IFACE$" | cut -d: -f1)
        if [ -n "$CONN_NAME" ]; then
            echo "Modifying connection: $CONN_NAME (device: $IFACE)"
            nmcli connection modify "$CONN_NAME" ipv4.ignore-auto-dns yes
            nmcli connection modify "$CONN_NAME" ipv4.dns "$PIHOLE_IP"
            nmcli connection up "$CONN_NAME"
        else
            echo "Warning: No active connection found for device $IFACE"
        fi
    done
    echo "DNS set to Pi-hole ($PIHOLE_IP) for all active interfaces."
fi

# Show new DNS settings
for IFACE in $ACTIVE_IFACES; do
    echo "DNS for $IFACE:"
    nmcli device show "$IFACE" | grep 'IP4.DNS'
done

# Add a manual host check to verify DNS changes
echo -e "\nChecking DNS resolution for argocd.soyspray.vip:"
host argocd.soyspray.vip || echo "WARNING: DNS resolution failed. Changes may take time to apply."
