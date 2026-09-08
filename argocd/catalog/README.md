# Argo application catalog

This folder contains the direct Argo CD ownership definitions that do not live
with an adopted application package. The native `soyspray` root applies them.

Normal releases merge checked changes to GitHub `main`. Argo CD then reconciles
the root and its children. Do not submit these Applications through Ansible.

Keep each Application name, destination, workload path, and data identity stable.
Use a recovery or retirement playbook for destructive operations.
