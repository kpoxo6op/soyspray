# Private assembly helper preview

This operation copies the three static files of Boris's assembly helper to
`node-1` and exposes the directory with **Tailscale Serve only**. It creates no
Kubernetes resources, public DNS record, ingress, or Funnel. The private site
files stay outside this public repository.

This tailnet does not currently issue Tailscale HTTPS certificates on node-1,
so Serve uses HTTP on port 80 inside Tailscale's encrypted connection.

From the operator laptop, set `ASSEMBLY_GUIDE_SOURCE_DIR` to a directory with
`index.html`, `app.js`, and `app.css`. Review the target directory and the empty
Tailscale Serve configuration on `node-1`, then run:

```sh
source soyspray-venv/bin/activate
ASSEMBLY_GUIDE_SOURCE_DIR=/absolute/path/to/site ansible-playbook \
  -i inventory/soycluster/hosts.yml \
  playbooks/operations/networking/serve-private-assembly-guide.yml \
  --become --become-user=root --user ubuntu
```

Open the private HTTP URL reported by `tailscale serve status` on a device
connected to the tailnet. Re-running the playbook updates the static files without changing an
existing Serve configuration. It can replace the initial, certificate-blocked
HTTPS route only when that route is the sole Serve route. It stops if another
Serve route or a Funnel is present. To retire this dedicated route, first confirm it is still the sole
Serve route on `node-1`, then run `sudo tailscale serve reset` there; the static
files can be removed separately. Do not reset a node with unrelated routes.

Checks: the playbook validates its source, node identity, and Serve state. After
deployment, fetch the page and assets over Tailscale and verify no Funnel is
enabled. This preview has no durable data or backup requirement.
