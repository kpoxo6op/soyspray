# Soyspray

Home Cluster created with Kubespray on Soyo miniPCs.

## Network Configuration

The router DHCP range was updated to 192.168.1.50-192.168.1.99.

Static IPs were
assigned to the miniPCs by MAC address: 192.168.1.100, 192.168.1.101, and
192.168.1.102.

Static IP assignment only worked using the Asus router mobile
app. The web GUI produced an "invalid MAC" error.

## System Installation

Ubuntu Server 24.04 was installed on the Soyo miniPCs using autoinstall.

Ethernet drivers for the Motorcomm ethernet adapter were compiled during the
autoinstall process.

## Repo Setup

This repository was created using guidance from Farhad's video, Kubespray's
`integration.md`, and Kubespray Ansible installation docs.

A virtual environment
(venv) was used for dependency management. Kubespray was integrated as a
submodule in this repository.
