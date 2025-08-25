# Tailscale

These playbooks install or remove the Tailscale client on the Kubernetes home node.

## Get an auth key
1. Sign in to the [Tailscale admin console](https://login.tailscale.com/admin/settings/keys).
2. Generate an auth key and copy it.
3. Add the key to `.env` as `TS_AUTH_KEY`.

```bash
TS_AUTH_KEY=tskey-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Install
Run the playbook from the repo root:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/install-tailscale.yml
```

The playbook fails with a clear error if `TS_AUTH_KEY` is missing.

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
