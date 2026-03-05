# OpenClaw Operations

Runbooks for OpenClaw installation, runtime control, and Gmail/webhook integration.

## Canonical entrypoints

- `openclaw-install.yml` - one-command bootstrap: preflight → host/dependency install → baseline config → kubeconfig → enable gateway boot-start → final status
- `openclaw-remove.yml` - one-command teardown: disable boot-start → remove install-mode config → remove kubeconfig → remove dependencies → remove host/user and service
- `openclaw-enable-tools.yml` - enable optional tool capabilities in one pass (`file`, `exec`, `browser`)
- `openclaw-disable-tools.yml` - disable optional tool capabilities in one pass (`browser`, `exec`, `file`)
- `configure-openclaw-oauth-token.yml` - reconfigure OpenClaw OAuth auth token non-interactively from env vars (`OPENCLAW_OAUTH_ACCESS_TOKEN`, optional `OPENCLAW_OAUTH_REFRESH_TOKEN`, optional `OPENCLAW_OAUTH_EXPIRES_IN`)

To force a CLI refresh/upgrade on an existing host run:

- `ansible-playbook playbooks/operations/openclaw/openclaw-install.yml -e "openclaw_upgrade=true"`

You can also limit scope to the host step with tags:

- `ansible-playbook playbooks/operations/openclaw/openclaw-install.yml -t openclaw-host -e "openclaw_upgrade=true"`

Use tags to narrow a tool pass:

- `-t openclaw-tools-file` for `group:fs`
- `-t openclaw-tools-exec` for `exec`
- `-t openclaw-tools-browser` for `browser`/Playwright stack

## Legacy one-purpose playbooks

Kept for direct targeting and rollback scripting:

- `audit-openclaw-security.yml`
- `configure-openclaw-exec-tool.yml`
- `configure-openclaw-file-tool.yml`
- `configure-openclaw-full-web-browsing.yml`
- `configure-openclaw-installation-mode.yml`
- `configure-openclaw-kubeconfig.yml`
- `disable-openclaw-exec-tool.yml`
- `disable-openclaw-file-tool.yml`
- `disable-openclaw-full-web-browsing.yml`
- `disable-openclaw-gateway-autostart.yml`
- `enable-openclaw-gateway-autostart.yml`
- `install-openclaw-dependencies.yml`
- `install-openclaw-host.yml`
- `remove-openclaw-dependencies.yml`
- `remove-openclaw-host.yml`
- `remove-openclaw-installation-mode.yml`
- `remove-openclaw-kubeconfig.yml`
- `show-openclaw-installation-mode-status.yml`
- `show-openclaw-preflight.yml`

## One-liner for OAuth refresh token update

```bash
OPENCLAW_OAUTH_ACCESS_TOKEN='<new-access-token>' \
OPENCLAW_OAUTH_REFRESH_TOKEN='<new-refresh-token>' \
OPENCLAW_OAUTH_EXPIRES_IN='30d' \
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/configure-openclaw-oauth-token.yml
```

## One-liner bootstrap with optional OAuth token refresh

```bash
OPENCLAW_OAUTH_ACCESS_TOKEN='<new-access-token>' \
OPENCLAW_OAUTH_REFRESH_TOKEN='<new-refresh-token>' \
OPENCLAW_OAUTH_EXPIRES_IN='30d' \
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/openclaw-install.yml
```

When `OPENCLAW_OAUTH_ACCESS_TOKEN` is set, the installer writes the value into
`~/.openclaw/agents/main/agent/auth-profiles.json` for `openai-codex` and restarts the gateway in the same run.

If no token is provided, the runbook now skips token reconfiguration without failing.

### If onboarding reports `health check failed: gateway closed`

That message usually means the onboarding flow could not keep a daemon running in this host environment. Fix it by letting the OpenClaw systemd gateway service own startup:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/enable-openclaw-gateway-autostart.yml
```

Then verify:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/show-openclaw-installation-mode-status.yml
```

For jobs that need Facebook web scraping, also enable browser tooling before running tasks:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/openclaw-enable-tools.yml
```

## Expose gateway UI from another device on your home LAN

Keep your current token auth, but bind the gateway to LAN interfaces:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/configure-openclaw-installation-mode.yml \
  -e openclaw_gateway_bind=lan \
  -e openclaw_gateway_port=18789

ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/enable-openclaw-gateway-autostart.yml \
  -e openclaw_gateway_bind=lan \
  -e openclaw_gateway_port=18789
```

Then open from your PC:

```bash
http://<node-ip>:18789
```

If you want to keep token mode, preserve the generated token suffix from the
Control UI/dashboard URL and append it as `#token=...`.

## How to fetch the OAuth token for OpenAI

Run the interactive OAuth flow once on a machine where a browser is available:

```bash
sudo su - openclaw
openclaw onboard --auth-choice openai-codex
```

`openclaw models auth login --provider openai-codex` is no longer supported in
current 2026.3.2 builds because provider plugins are optional and not bundled for
`openai-codex`.

If your host supports persistent daemon install, you can run:

```bash
sudo su - openclaw
openclaw onboard --install-daemon --auth-choice openai-codex
```

If onboarding still shows `gateway closed`, keep using the non-daemon flow above and
recover the gateway using the Ansible recovery block in the section above.

Then extract the access token:

```bash
sudo -n su - openclaw -c "jq -r '.profiles[\"openai-codex:default\"].access' ~/.openclaw/agents/main/agent/auth-profiles.json"
```

Copy that value into `OPENCLAW_OAUTH_ACCESS_TOKEN` and rerun the playbook command above.

If you see `refresh_token_reused` in gateway logs, the token was invalidated by a
previous re-auth attempt and must be replaced. Re-run the browser OAuth flow to
generate a fresh code and paste the resulting `openai-codex:default` token again.
