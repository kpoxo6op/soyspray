# Tailscale

These playbooks install or remove the Tailscale client on the Kubernetes home node.

## Get an auth key
1. Sign in to the [Tailscale admin console](https://login.tailscale.com/admin/settings/keys).
2. Generate a reusable auth key. Set the expiry to the maximum allowed (90 days).
3. Add the key to `.env` as `TS_AUTH_KEY` for the first run.
4. After the node joins the tailnet, disable key expiry for the node in the Machines page and remove `TS_AUTH_KEY` from `.env`.

```bash
TS_AUTH_KEY=tskey-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Install
Run the playbook from the repo root. **Important**: Activate the Python virtual environment and source the `.env` file first to load the auth key:

```bash
source soyspray-venv/bin/activate
set -a && source .env && set +a
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/install-tailscale.yml
```

The playbook fails with a clear error if `TS_AUTH_KEY` is missing and the node has not authenticated yet.

## Configure DNS for *.soyspray.vip domains

To access services like `https://qbittorrent.soyspray.vip/` from other devices in the tailnet:

1. **Go to [Tailscale Admin Console](https://login.tailscale.com/admin/dns)**
2. **In Nameservers section:**
   - Keep existing Cloudflare DNS (`1.1.1.1`) for general internet
   - Verify Pi-hole DNS (`192.168.50.202`) is added for local resolution
3. **In Search Domains section:**
   - Add: `soyspray.vip`
   - This ensures `*.soyspray.vip` domains resolve through Pi-hole
4. **Enable MagicDNS** (if not already enabled)

## Test connectivity
Use the Tailscale CLI to verify the node joined the network:

```bash
tailscale status
tailscale ping <other-node>
```

Test DNS resolution from other devices:
```bash
# Should resolve to 192.168.50.200
nslookup qbittorrent.soyspray.vip
```

## Remove
To remove the client, run:

```bash
# Activate the Python virtual environment
source soyspray-venv/bin/activate

# Run the Tailscale removal playbook
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/remove-tailscale.yml
```
