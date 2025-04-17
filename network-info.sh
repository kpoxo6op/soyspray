#!/bin/bash

# This script gathers comprehensive networking information related to the Wireguard hub-and-spoke setup
# It collects data from all nodes in the cluster with special focus on the Wireguard gateway node
# and verifies connectivity through the Azure VPS intermediary

# Array of nodes to check (all K8s nodes)
NODES=("192.168.1.100" "192.168.1.101" "192.168.1.102" "192.168.1.103")
USER="ubuntu"

# VPS and Wireguard details
VPS_IP="AZURE_VPS_PUBLIC_IP"  # Replace with your actual Azure VPS IP
WIREGUARD_VPS_IP="10.8.0.1"
WIREGUARD_HOME_IP="10.8.0.3"
WIREGUARD_INTERFACE="wg0-home"
WIREGUARD_VPS_PORT="51820"
CLUSTER_NETWORK="192.168.1.0/24"

# Basic networking commands for all nodes
BASIC_COMMANDS=(
    "hostname"
    "ip -br addr"                                    # Network interfaces brief
    "ip -br link"                                    # Link status
    "ip route"                                       # Routing table
    "ip rule"                                        # Routing policy
    "cat /proc/sys/net/ipv4/ip_forward"             # IP forwarding status
    "ping -c 3 192.168.1.1 || echo 'Ping failed'"   # Default gateway ping
    "netstat -tuln | grep -E '(51820|6443)'"        # Check for Wireguard and K8s API ports
)

# Advanced networking commands for all nodes
ADVANCED_COMMANDS=(
    "sudo iptables -t nat -L POSTROUTING -v -n"     # NAT rules
    "sudo iptables -L FORWARD -v -n"                # Forwarding rules
    "ip neigh"                                       # ARP table
    "traceroute -n 8.8.8.8 || echo 'Traceroute failed'"  # Internet routing path
    "ss -tuap | grep -i kube"                        # Kubernetes networking sockets
    "sudo tcpdump -i any -c 5 -n udp port 51820 || echo 'No Wireguard packets captured'"  # Capture Wireguard packets briefly
)

# Wireguard-specific commands (for the gateway node running Wireguard - Node-A)
WIREGUARD_COMMANDS=(
    "sudo wg show all"                               # Wireguard status
    "sudo wg showconf ${WIREGUARD_INTERFACE} || echo 'No Wireguard config found'"  # Wireguard config
    "sudo cat /etc/wireguard/${WIREGUARD_INTERFACE}.conf || echo 'Config file not found'"  # Config file
    "ping -c 3 ${WIREGUARD_VPS_IP} || echo 'Cannot ping VPS Wireguard IP'"  # Test VPS Wireguard connectivity
    "sudo systemctl status wg-quick@${WIREGUARD_INTERFACE} || echo 'Wireguard service not found'"  # Wireguard service status
    "journalctl -u wg-quick@${WIREGUARD_INTERFACE} --no-pager --lines=20 || echo 'No logs found'"  # Wireguard logs
)

# Kubernetes networking commands
K8S_COMMANDS=(
    "kubectl get nodes -o wide"                      # Node network info
    "kubectl get svc -A -o wide"                     # Service network info
    "kubectl get pods -A -o wide | grep -i calico"   # Network plugin pods
    "kubectl -n kube-system get pods -l k8s-app=calico-node -o wide"  # Calico status
    "kubectl -n kube-system get pods -l k8s-app=kube-dns -o wide"     # DNS status
    "kubectl get networkpolicy -A"                   # Network policies
    "kubectl get ingressclass -A"                    # Ingress classes
)

# Function to gather basic info from all nodes
gather_basic_node_info() {
    local node=$1
    echo "==============================================="
    echo "Gathering basic network information from node: $node"
    echo "==============================================="

    for cmd in "${BASIC_COMMANDS[@]}"; do
        echo ""
        echo "--- Running: $cmd ---"
        ssh -o StrictHostKeyChecking=no $USER@$node "$cmd" || echo "Failed to run $cmd"
        echo "-------------------"
    done
    echo ""
}

# Function to gather advanced info from all nodes
gather_advanced_node_info() {
    local node=$1
    echo "==============================================="
    echo "Gathering advanced network information from node: $node"
    echo "==============================================="

    for cmd in "${ADVANCED_COMMANDS[@]}"; do
        echo ""
        echo "--- Running: $cmd ---"
        ssh -o StrictHostKeyChecking=no $USER@$node "$cmd" || echo "Failed to run $cmd"
        echo "-------------------"
    done
    echo ""
}

# Function to gather Wireguard info from the gateway node (Node-A)
gather_wireguard_info() {
    local node=$1
    echo "==============================================="
    echo "Gathering Wireguard information from node: $node"
    echo "==============================================="

    for cmd in "${WIREGUARD_COMMANDS[@]}"; do
        echo ""
        echo "--- Running: $cmd ---"
        ssh -o StrictHostKeyChecking=no $USER@$node "$cmd" || echo "Failed to run $cmd"
        echo "-------------------"
    done
    echo ""
}

# Function to gather Kubernetes network info (from one control plane node)
gather_k8s_network_info() {
    local node=$1
    echo "==============================================="
    echo "Gathering Kubernetes network information from node: $node"
    echo "==============================================="

    for cmd in "${K8S_COMMANDS[@]}"; do
        echo ""
        echo "--- Running: $cmd ---"
        ssh -o StrictHostKeyChecking=no $USER@$node "$cmd" || echo "Failed to run $cmd"
        echo "-------------------"
    done
    echo ""
}

# Function to perform Wireguard connectivity tests
test_wireguard_connectivity() {
    local node=$1
    echo "==============================================="
    echo "Testing Wireguard connectivity from node: $node"
    echo "==============================================="

    echo ""
    echo "--- Testing outbound connection to VPS ---"
    ssh -o StrictHostKeyChecking=no $USER@$node "ping -c 3 ${VPS_IP} || echo 'Cannot ping VPS public IP'"

    echo ""
    echo "--- Testing Wireguard tunnel to VPS ---"
    ssh -o StrictHostKeyChecking=no $USER@$node "ping -c 3 ${WIREGUARD_VPS_IP} || echo 'Cannot ping VPS Wireguard IP'"

    echo ""
    echo "--- Testing DNS resolution through tunnel ---"
    ssh -o StrictHostKeyChecking=no $USER@$node "nslookup google.com || echo 'DNS resolution failed'"

    echo ""
    echo "--- Checking Wireguard handshake ---"
    ssh -o StrictHostKeyChecking=no $USER@$node "sudo wg show ${WIREGUARD_INTERFACE} latest-handshakes || echo 'No handshake info'"

    echo ""
    echo "--- Testing bidirectional UDP connectivity to VPS (requires netcat) ---"
    ssh -o StrictHostKeyChecking=no $USER@$node "nc -zu -w 3 ${VPS_IP} ${WIREGUARD_VPS_PORT} && echo 'UDP port is reachable' || echo 'UDP port test failed'"

    echo "-------------------"
    echo ""
}

# Main execution
echo "Starting network information gathering..."
echo "$(date)"
echo ""

# First gather basic networking info from all nodes
for node in "${NODES[@]}"; do
    gather_basic_node_info $node
done

# Then gather more detailed network info from all nodes
for node in "${NODES[@]}"; do
    gather_advanced_node_info $node
done

# Get Wireguard info from the first node (Node-A/control plane acting as gateway)
echo "Getting Wireguard information from Node-A (gateway node)..."
gather_wireguard_info "${NODES[0]}"

# Test Wireguard connectivity
echo "Testing Wireguard connectivity..."
test_wireguard_connectivity "${NODES[0]}"

# Gather Kubernetes network info from the first control plane node
echo "Gathering Kubernetes network information..."
gather_k8s_network_info "${NODES[0]}"

echo "Network information gathering complete"
echo "$(date)"
