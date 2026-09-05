# Domain check runtime

`domain-health-exporter.py` uses Python's standard library to check RDAP expiry,
Cloudflare zone state, and public nameservers. It exposes `/metrics` and
`/healthz` on port 8080 and reports each scheduled run to the existing Healthchecks
identity. Read the [app README](../README.md) for deployment and private inputs.

The current Kustomize package still supplies this exact script through its
existing ConfigMap. Immutable image packaging follows as a separate change.
Do not change checks or metrics while moving the runtime source.
