#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Kubernetes Node Resource Usage ===${NC}"
echo ""

# Get node resource allocation
echo -e "${YELLOW}Node Resource Allocation:${NC}"
kubectl describe nodes | grep -A 20 "Allocated resources" | grep -A 8 "Resource"

echo ""
echo -e "${GREEN}=== Pod Resource Details ===${NC}"
echo ""

# Get detailed pod resource allocation per node
echo -e "${YELLOW}Pod Resource Allocation by Node:${NC}"
kubectl describe nodes | grep -A 30 "Non-terminated Pods"

echo ""
echo -e "${YELLOW}Pod Resources by Namespace:${NC}"
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
    echo -e "\n${GREEN}Namespace: ${ns}${NC}"
    kubectl -n $ns get pods -o custom-columns="NAME:.metadata.name,CPU_REQ:.spec.containers[*].resources.requests.cpu,MEM_REQ:.spec.containers[*].resources.requests.memory" | sort -k2 -r
done

echo ""
echo -e "${YELLOW}Pod Distribution Across Nodes:${NC}"
kubectl get pods -A -o wide

echo ""
echo -e "${YELLOW}Nodes Status:${NC}"
kubectl get nodes -o custom-columns="NODE:.metadata.name,CONDITIONS:.status.conditions[*].type"
