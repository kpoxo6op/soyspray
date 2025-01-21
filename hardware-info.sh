#!/bin/bash

# Array of nodes to check
NODES=("192.168.1.100" "192.168.1.101" "192.168.1.102")
USER="ubuntu"

# Commands to run
COMMANDS=(
    "hostname"
    "lscpu | grep -E 'CPU\(s\)|Thread|Core|Model name'"  # CPU info
    "free -h"                                            # Memory info
    "df -h /"                                           # Root disk space
    "lsblk -d -o NAME,SIZE,MODEL,ROTA"                  # Physical disks
    "ip -br addr"                                       # Network interfaces
    "cat /proc/meminfo | grep -E 'MemTotal|SwapTotal'"  # Detailed memory
    "nproc"                                             # Number of processors
)

# Function to gather info from a node
gather_node_info() {
    local node=$1
    echo "==============================================="
    echo "Gathering hardware information from node: $node"
    echo "==============================================="

    for cmd in "${COMMANDS[@]}"; do
        echo ""
        echo "--- Running: $cmd ---"
        ssh -o StrictHostKeyChecking=no $USER@$node "$cmd" || echo "Failed to run $cmd"
        echo "-------------------"
    done
    echo ""
}

# Main execution
echo "Starting hardware information gathering..."
echo "$(date)"
echo ""

for node in "${NODES[@]}"; do
    gather_node_info $node
done

echo "Hardware information gathering complete"
echo "$(date)"
