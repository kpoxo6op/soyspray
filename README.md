# Soyspray 🌱💦

Home Cluster created with Kubespray on Soyo miniPCs.

## Network Configuration

The router DHCP range was updated to 192.168.1.50-192.168.1.99.

Static IPs were assigned to the miniPCs by MAC address: 192.168.1.100,
192.168.1.101, and 192.168.1.102.

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
declare -a IPS=(node-0,192.168.1.100 node-1,192.168.1.101 node-2,192.168.1.102)
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

## Testing

Install requirements and run the Flask tests with pytest:

```sh
pip install -r flask_test/requirements.txt pytest
pytest flask_test/test_app.py
```
