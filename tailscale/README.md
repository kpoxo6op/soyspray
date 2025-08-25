# Tailscale

These playbooks install or remove the Tailscale client on the Kubernetes home node.

## Get an auth key
1. Sign in to the [Tailscale admin console](https://login.tailscale.com/admin/settings/keys).
2. Generate a reusable auth key and set **Expiry** to **Never**.
3. Add the key to `.env` as `TS_AUTH_KEY` for the first run.
4. After the node joins the tailnet, remove `TS_AUTH_KEY` from `.env`.

```bash
TS_AUTH_KEY=tskey-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Install
Run the playbook from the repo root:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/install-tailscale.yml
```

The playbook fails with a clear error if `TS_AUTH_KEY` is missing and the node has not authenticated yet.

## Test connectivity
Use the Tailscale CLI to verify the node joined the network:

```bash
tailscale status
tailscale ping <other-node>
```

## Remove
To remove the client, run:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/remove-tailscale.yml
```
