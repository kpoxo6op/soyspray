# Kong bank lab Ansible role

This role manages the lab's Argo CD definitions and runtime-generated demo
credentials. It is the supported state-changing entry point for switching the
lab on or off.

- [`defaults/`](defaults/) declares the parked default, target revision,
  runtime applications, and credential list.
- [`tasks/`](tasks/) separates shared project setup, startup, and shutdown.

The root `Makefile` exposes the normal commands:

```text
make kong-on
make kong-off
```

Both commands run the repository preflight before Ansible changes application
state. The Argo project and Kong CRDs remain available while the runtime is off.
