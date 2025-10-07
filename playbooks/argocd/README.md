# Argo CD manifests

This directory groups the Kubernetes resources that back the Argo CD
playbooks.  The content is split by concern so the intent of each file is
immediately obvious:

- `config/` – bootstrap manifests that shape the core Argo CD installation
  (service, ingress, config maps, etc.).
- `apps/` – per-application definitions that Argo CD reconciles once the
  platform is online.

The playbooks now reference these folders explicitly (via `playbook_dir`) so
manifests no longer need to live in a generic `yaml/` bucket.
