# Playbooks

Organized Ansible playbooks for Kubernetes cluster management and GitOps operations.

## Structure

### argocd/
ArgoCD-related playbooks, configuration, and application definitions.

- playbooks/ - Ansible playbooks for ArgoCD deployment and configuration
- config/ - ArgoCD controller configuration files
- applications/ - GitOps application definitions organized by domain

### operations/
Cluster operation playbooks organized by functional area.

- nodes/ - Node management and configuration
- networking/ - Network setup and tools
- storage/ - Storage initialization and management
- security/ - Security and certificate management
- examples/ - Example and utility playbooks

### experiments/
Experimental playbooks and proof-of-concepts.

## Usage

### ArgoCD Operations

```bash
# Deploy all ArgoCD applications
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu argocd/playbooks/deploy-apps.yml

# Configure ArgoCD ingress
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu argocd/config/argocd-configure-ingress.yml
```

### Node Operations

```bash
# Install node tools
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu operations/nodes/install-node-tools.yml

# Restart nodes
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu operations/nodes/restart-node.yml
```

### Storage Operations

```bash
# Initialize Longhorn storage
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu operations/storage/initialize-longhorn-storage.yml
```

## Application Domains

Applications are organized into domains for better management:

- infrastructure/ - Core cluster infrastructure
- database/ - Database operators and instances
- media/ - Media stack applications
- observability/ - Monitoring and logging
- backups/ - Backup solutions

## Naming Convention

Playbooks follow the pattern: `verb-subject.yml`

Examples:
- deploy-apps.yml
- install-tailscale.yml
- restart-node.yml
- initialize-longhorn-storage.yml

