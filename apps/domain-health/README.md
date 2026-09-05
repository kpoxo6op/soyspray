# Domain health

The exporter checks domain expiry, Cloudflare zone status, and authoritative
nameservers. Prometheus reads its metrics, and the existing Healthchecks identity
receives its scheduled result. Keep these checks independent of laptop diagnosis.

The native root owns the existing Application and a dedicated AppProject. The app
keeps its manifests in `manifests/` and source in `app/`. Its Service, Deployment,
ConfigMap, namespace, and two Secret identities stay in place. The app-local
Kustomize package preserves the active workload. During image migration, it reads
the frozen `manifests/legacy-exporter.py`. Source edits under `app/` build an image
and open a separate digest promotion; they do not change the running exporter.

```sh
make check APP=domain-health
make deploy APP=domain-health REVISION=YOUR_PUSHED_BRANCH
make status APP=domain-health FORMAT=json
```

Deployment runs the full gate and standard Ansible bootstrap and root procedure.
After merge, run `make deploy APP=domain-health` to return to HEAD. Verify the
exact Argo comparison, original resource and pod identities, Secret hashes,
metrics scrape, recent successful checks, and the independent check identity.
Diff, smoke, and isolated recovery are unknown until maintained operations exist.

Bootstrap preserves the two existing Secrets. Matching inputs make no change;
conflicting or incomplete inputs stop before any writes. Missing Secrets use
native create, so a competing creation is not overwritten. Check mode validates
inputs and skips Secret creation. This path does not read `.env` or rotate tokens.

For missing identities, restore these values from an off-cluster Ansible Vault
file: `domain_health_cloudflare_api_token`, `domain_health_healthchecks_ping_url`,
and `domain_health_expected_nameservers`. The last value is a comma-separated
nameserver list. Keep the original provider and Healthchecks identities. Keep the
Vault password outside the cluster. Use the inventory and privilege options in
AGENTS.md with `apps/domain-health/bootstrap.yml --ask-vault-pass
-e @/private/domain-health.vault.yml`, first with `--check`, then without it.

The app has no persistent volume. Preserve its private bootstrap inputs for
recovery. A full recreation and independent delivery check remain unknown.
Rollback restores the reviewed Application source and project through Ansible;
do not delete the app, namespace, or identities as a rollback step.

## Build and promote the runtime

The Dockerfile uses the exact upstream Python base digest previously observed
on the live exporter. The image contains only the standard-library runtime,
runs as UID 1000, and installs no startup patches. GitHub checks the image without
external network access, including its real entrypoint and HTTP failure state.

A source merge publishes a tested GHCR image and opens a draft promotion. The
promotion changes the digest and removes the old script command, mount, volume,
and ConfigMap generator together. It preserves environment Secret references,
selectors, resources, ports, and probes. Do not merge or deploy automatically.
Remove the frozen source only after the image and live domain checks are verified.

Run `make check APP=domain-health` locally and review the image workflow result.
Docker is needed only for the native image checks; GitHub runs them when it is
unavailable locally. Roll back the digest and dependent configuration together.
For the initial transition, restore the previous script configuration and use
the upstream Python digest recorded in the Dockerfile if rollback is needed.
