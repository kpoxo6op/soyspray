.DEFAULT_GOAL := help

K8S_USER        := ubuntu
WORKER_NODE1    := 192.168.1.103
WORKER_NODE2    := 192.168.1.103
WORKER_NODE3    := 192.168.1.103
MASTER_NODE     := 192.168.1.103

# Adjust ArgoCD version if needed
ARGOCD_VERSION  := v2.12.4

master:
	ssh $(K8S_USER)@$(MASTER_NODE)

worker1:
	ssh $(K8S_USER)@$(WORKER_NODE1)

worker2:
	ssh $(K8S_USER)@$(WORKER_NODE2)

worker3:
	ssh $(K8S_USER)@$(WORKER_NODE3)

argo:
	argocd login argocd.soyspray.vip --username admin --password password --grpc-web

VENV_NAME       := soyspray-venv

venv:
	python3 -m venv $(VENV_NAME)
	@echo "Virtual environment created. To activate, run: source $(VENV_NAME)/bin/activate"

act:
	@echo "source $(VENV_NAME)/bin/activate"

ans:
	@echo "\nansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/ --tags TAG\n"
	@echo "ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml\n"


install:
	@if [ ! -w /usr/local/bin ]; then \
		echo "Error: This target requires sudo privileges. Please run 'sudo make install'"; \
		exit 1; \
	fi

	@if ! dpkg -l | grep -q "^ii  python3-pip " || ! dpkg -l | grep -q "^ii  python3-venv "; then \
		echo "Installing Python packages..."; \
		sudo apt-get update && sudo apt-get install python3-pip python3-venv -y; \
	else \
		echo "Python packages already installed: python $$(python3 --version), pip $$(pip3 --version | cut -d' ' -f2)"; \
	fi

	@if command -v kubectl >/dev/null 2>&1; then \
		echo "kubectl already installed. Version info:"; \
		kubectl version --client 2>&1 || true; \
	else \
		echo "Installing kubectl..."; \
		curl -LO "https://dl.k8s.io/release/$$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"; \
		sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl; \
		rm -f kubectl; \
	fi

	@if command -v argocd >/dev/null 2>&1 && argocd version --client >/dev/null 2>&1; then \
		echo "ArgoCD CLI already installed and working:"; \
		argocd version --client | head -1; \
	else \
		echo "Installing ArgoCD CLI $(ARGOCD_VERSION)..."; \
		sudo curl -L -o /usr/local/bin/argocd \
			https://github.com/argoproj/argo-cd/releases/download/$(ARGOCD_VERSION)/argocd-linux-amd64; \
		sudo chmod +x /usr/local/bin/argocd; \
	fi

go: argo act ans

alist:
	@./scripts/argocd-list.sh "$(COLS)"


help:
	@echo "Available commands:"
	@echo "  make master      - SSH into master node ($(MASTER_NODE))"
	@echo "  make worker1     - SSH into worker node 1 ($(WORKER_NODE1))"
	@echo "  make worker2     - SSH into worker node 2 ($(WORKER_NODE2))"
	@echo "  make worker3     - SSH into worker node 3 ($(WORKER_NODE3))"
	@echo "  make install     - Install tools (requires sudo: run 'sudo make install')"
	@echo "  make argo        - Login to ArgoCD (argocd.soyspray.vip)"
	@echo "  make act         - Show command to activate Python virtual environment"
	@echo "  make ans         - Show Ansible command starter"
	@echo "  make go          - Run argo, act, and ans commands in sequence"
	@echo "  make alist       - List ArgoCD apps with scripts/argocd-list.sh"
.PHONY: master worker1 worker2 worker3 help venv act argo install go alist
