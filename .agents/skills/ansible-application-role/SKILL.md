---
name: ansible-application-role
description: Build or review Ansible roles that manage Argo CD applications and Kubernetes resources. Use for role defaults, task decomposition, enable or disable lifecycles, secret creation, idempotency, check mode, ansible-lint, and safe GitOps deployment workflows.
---

# Ansible Application Role

Treat a role as a declarative state transition with a small public interface.

## Workflow

1. Read the repository instructions, canonical playbook, inventory, and a nearby role before editing.
2. Define operator inputs in `defaults/main.yml`. Prefer `enabled`, `target_revision`, and compact resource lists over duplicated tasks.
3. Keep `tasks/main.yml` as a readable dispatcher. Split lifecycle phases into files such as `project.yml`, `enabled.yml`, and `disabled.yml` when each phase can be understood independently.
4. Use fully qualified module names. Give every task an outcome-oriented name and keep secret-bearing tasks under `no_log: true`.
5. Prefer `state: present` or `state: absent` and idempotent modules. Query before generating credentials so a second run preserves them.
6. Preserve ownership boundaries: Ansible should create Argo definitions and runtime-only secrets; Argo should own workload resources.
7. Quiesce Argo Applications before disabling them: remove automatic sync and any in-progress operation with a metadata-only patch, then delete each Application by API identity. Do not reapply a checked-in Application immediately before deletion: that can replace a live temporary branch revision with `HEAD` and strand Argo's resource finalizer when the path is not on the default branch yet.
8. Test the role's public behavior before implementation. Cover defaults, enabled resources, disabled resources, ordering, secret persistence, and revision propagation.
9. Run `ansible-lint` from the repository root against the changed task/default files. Run the playbook syntax check with the project inventory.
10. Follow the repository's branch, push, preflight, and deployment rules. Never turn a code review into an ad hoc cluster mutation.

## Review questions

- Can an operator predict exactly what a second run changes?
- Does disabling remove runtime cost without deleting durable shared definitions?
- Are waits tied to observable conditions instead of fixed sleeps?
- Is destructive ordering explicit and reversed where dependencies require it?
- Are branch revisions propagated to every Git-backed runtime consumer?
- Can failures be retried safely without rotating credentials or orphaning resources?

Use current Ansible documentation for version-specific module behavior. Do not copy a generic role layout over established repository conventions.
