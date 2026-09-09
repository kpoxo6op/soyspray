# Soyspray

Soyspray is the home system that runs personal services across a three-node
Kubernetes cluster. This guide starts with what the system does and how to use
it. Detailed implementation and recovery procedures remain beside the code.

## Find what you need

- [Services](services.md) explains the main applications and where their
  technical details live.
- [Everyday operations](operations.md) gives the supported ways to check the
  system and make changes.
- [Recovery](recovery.md) explains what backup and restore evidence means.
- [Architecture](architecture.md) shows which tool owns each part of the system.
- [Ask an agent](ask-an-agent.md) provides useful requests and the evidence an
  agent should return.

## Working rule

Changes go through a GitHub pull request. Argo CD owns application workloads.
Kubespray and Ansible own the cluster foundation and deliberate operations.
Agents must report missing evidence as unknown instead of assuming success.

## Technical source

Open the [Soyspray repository](https://github.com/kpoxo6op/soyspray) for the
current code, pull requests, and detailed README files.

