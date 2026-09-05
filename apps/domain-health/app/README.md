# Domain check runtime

`domain-health-exporter.py` uses Python's standard library to check RDAP expiry,
Cloudflare zone state, and public nameservers. It exposes `/metrics` and
`/healthz` on port 8080 and reports each scheduled run to the existing Healthchecks
identity. Read the [app README](../README.md) for deployment and private inputs.

The Dockerfile packages this source. Source merges build an image and open a
separate digest promotion. During the initial transition, Kustomize reads the
frozen copy in `manifests/legacy-exporter.py`, so new source cannot change the
running ConfigMap. The same standard-library runtime tests run locally and
inside the image.
