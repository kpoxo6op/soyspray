#!/bin/bash

# Array of nodes to check
NODES=("192.168.1.100" "192.168.1.101" "192.168.1.102")
USER="ubuntu"

# Commands to run
COMMANDS=(
    "hostname"
    "lsblk -f"
    "sudo fdisk -l"
    "sudo df -h"
    "sudo pvs"
    "sudo vgs"
    "sudo lvs"
    "echo '--- Local Storage Mounts ---' && sudo ls -l /mnt/disks/"
    "echo '--- Local PV Usage ---' && sudo df -h /mnt/disks/vol1"
)

# Function to gather info from a node
gather_node_info() {
    local node=$1
    echo "==============================================="
    echo "Gathering information from node: $node"
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
echo "Starting storage information gathering..."
echo "$(date)"
echo ""

for node in "${NODES[@]}"; do
    gather_node_info $node
done

echo "Storage information gathering complete"
echo "$(date)"
