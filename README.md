# Soyspray

Soyspray manages a home Kubernetes cluster provisioned with Kubespray and the
workloads that run on it through Ansible and Argo CD.

This branch also establishes the foundation for a Kong OSS bank-lab platform:
a realistic home-lab simulation of how a regulated bank platform team could run
Kong OSS on Kubernetes. The lab is intended to model controlled change,
ownership, policy gates, testing, evidence, rollback, and day-2 operations
without pretending that Kong Enterprise or Konnect features exist in OSS.

## Kong OSS Bank-Lab Foundation

The Kong bank lab is owned as a platform product. Future platform work should
be treated as if an Integration / Infrastructure platform team owns the Kong
runtime, GitOps model, shared policies, validation gates, documentation,
runbooks, and operational evidence.

Rule: nothing deployed without tests. A feature is not considered ready
just because a manifest applies. Future work must add validation, positive and
negative tests, documentation, rollback notes, and evidence reports appropriate
to the scope of the change.

Goal 000 only creates the repository foundation. It does not deploy Kubernetes
resources, install Kong, create secrets, or change the live cluster.

Goal 001 adds platform prerequisite definitions for namespaces, GitOps,
MetalLB, cert-manager, SOPS/age, NetworkPolicy, and explicit cluster smoke
checks. It still does not install Kong or apply resources automatically.

Goal 002 adds the Kong OSS baseline as declarative manifests, Helm values,
Gateway API smoke routes, Admin API exposure controls, and local validation.
It does not apply Kong to the cluster unless explicitly permitted.

Local validation commands for this foundation are:

```sh
make validate
make test
make policy-test
make docs
make evidence
```

Run the full local gate with:

```sh
make validate && make test && make policy-test && make docs && make evidence
```

The detailed programme roadmap is in [ROADMAP.md](ROADMAP.md). The archived
design notes and future goal bodies live under
[soydocs/kong-bank-lab](soydocs/kong-bank-lab/README.md).

## Existing Cluster Notes

The original home cluster was created with Kubespray on Soyo mini PCs. The
notes below are historical setup notes for that cluster.

## Network Configuration

The router DHCP range was updated to 192.168.50.50-192.168.50.199.

Static IPs were assigned to the miniPCs by MAC address: 192.168.50.100,
192.168.50.101, and 192.168.50.102.

Static IP assignment only worked using the Asus router mobile app. The web GUI
produced an "invalid MAC" error.

## System Installation

Ubuntu Server 24.04 was installed on the Soyo miniPCs using autoinstall.

Ethernet drivers for the Motorcomm ethernet adapter were compiled during the
autoinstall process.

## Repo Setup

This repository was created using guidance from Farhad's video, Kubespray's
`integration.md`, and Kubespray Ansible installation docs.

### Hosts YAML Generation

To generate the `hosts.yaml` file, the following steps were used:

```sh
# Copy sample inventory
# Declare the IPs and hostnames for the nodes
# Generate the hosts.yaml file
# View the generated hosts.yaml
cp -rfp inventory/sample inventory/soycluster
declare -a IPS=(node-0,192.168.50.100 node-1,192.168.50.101 node-2,192.168.50.102)
CONFIG_FILE=inventory/soycluster/hosts.yml python3 contrib/inventory_builder/inventory.py ${IPS[@]}
cat inventory/soycluster/hosts.yml
```

A virtual environment (`soyspray-venv`) was used for dependency management and
is included in `.gitignore` to keep environment-specific files out of the
repository. Kubespray was integrated as a submodule in this repository.

```sh
# Create virtual environment
# Activate virtual environment
# Install requirements from the kubespray submodule
python3 -m venv soyspray-venv
source soyspray-venv/bin/activate
cd kubespray
pip install -U -r requirements.txt
```
