.DEFAULT_GOAL := help

# Kubernetes nodes SSH shortcuts
K8S_USER = ubuntu

# Node IP addresses
MASTER_NODE = 192.168.1.100
WORKER_NODE1 = 192.168.1.101
WORKER_NODE2 = 192.168.1.102

# SSH commands
master:
	ssh $(K8S_USER)@$(MASTER_NODE)

worker1:
	ssh $(K8S_USER)@$(WORKER_NODE1)

worker2:
	ssh $(K8S_USER)@$(WORKER_NODE2)

# Python virtual environment
VENV_NAME = soyspray-venv

venv:
	python3 -m venv $(VENV_NAME)
	@echo "Virtual environment created. To activate, run: source $(VENV_NAME)/bin/activate"

act:
	@echo "source $(VENV_NAME)/bin/activate"

ans:
	@echo "\nansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/ --tags TAG\n"

bal:
	kubectl get pods -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODE:.spec.nodeName | grep -v "^NAMESPACE" | awk '{print $$3}' | sort | uniq -c

help:
	@echo "Available commands:"
	@echo "  make master    - SSH into master node ($(MASTER_NODE))"
	@echo "  make worker1   - SSH into worker node 1 ($(WORKER_NODE1))"
	@echo "  make worker2   - SSH into worker node 2 ($(WORKER_NODE2))"
	@echo "  make act       - Show command to activate Python virtual environment"
	@echo "  make ans       - Show Ansible command starter"
	@echo "  make bal       - Show pod count distribution across nodes"

.PHONY: master worker1 worker2 help venv act bal
