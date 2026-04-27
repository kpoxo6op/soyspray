# OpenClaw Installation Mode Plan

## Goal

Install OpenClaw on the Ubuntu mini PC in a hardened mode for:

- Telegram DM control (pairing-only)
- Public web research, with optional full browser automation when explicitly enabled
- `kubectl` execution, matching host SSH admin permissions
- ChatGPT Codex subscription auth (no OpenAI API key)

## Scope and guardrails

- Host-level setup is done on the mini PC (`192.168.20.10`).
- OpenClaw runs as dedicated user `openclaw`, not `root`.
- Gateway UI stays on localhost and is accessed only via SSH tunnel.
- OpenClaw Kubernetes access is provisioned using host admin kubeconfig, matching SSH admin context.

## Runbook Mapping

Primary flow is now consolidated into these two entrypoints:

- `openclaw-install.yml` - bootstrap install + deps + hardened config + kubeconfig + gateway autostart + status checks
- `openclaw-remove.yml` - teardown of gateway autostart, install-mode configs, kubeconfig, dependencies, and host identity

Legacy direct-run playbooks still exist for granular control:

- `configure-openclaw-full-web-browsing.yml` - install Chromium/Playwright and enable browser tool access
- `configure-openclaw-file-tool.yml` - remove filesystem deny block (`group:fs`) and enable file tooling
- `configure-openclaw-exec-tool.yml` - remove exec deny block and enable command execution tooling
- `configure-openclaw-installation-mode.yml` - write hardened runtime config and service settings
- `configure-openclaw-kubeconfig.yml` - copy `/etc/kubernetes/admin.conf` for matching Kubernetes privileges
- `disable-openclaw-exec-tool.yml` - re-add exec denial and remove exec from agent allowlist
- `disable-openclaw-file-tool.yml` - re-add `group:fs` deny and remove file tool from allowlist
- `disable-openclaw-full-web-browsing.yml` - disable browser tool and browser automation in OpenClaw config
- `disable-openclaw-gateway-autostart.yml` - stop and remove boot-start service
- `enable-openclaw-gateway-autostart.yml` - create and enable systemd service so OpenClaw starts after reboot
- `install-openclaw-dependencies.yml` - install Google Cloud CLI, `gog`, tailscale
- `install-openclaw-host.yml` - install host prerequisites and CLI
- `remove-openclaw-host.yml` - remove install, service user, and lingering state
- `remove-openclaw-installation-mode.yml` - remove hardened config only
- `remove-openclaw-kubeconfig.yml` - remove OpenClaw kubeconfig
- `remove-openclaw-dependencies.yml` - remove integration dependencies
- `show-openclaw-installation-mode-status.yml` - post-change verification
- `show-openclaw-preflight.yml` - initial readiness check before rollout
- `audit-openclaw-security.yml` - security review

## Current-state scouting (2026-02-15)

Read-only checks on `node-0` found:

- OpenClaw is not installed yet (`openclaw` binary absent).
- `openclaw` user/home do not exist yet.
- `kubectl` is installed at `/usr/local/bin/kubectl` (not `/usr/bin` or `/snap/bin`).
- `/etc/kubernetes/admin.conf` exists and maps to `kubernetes-admin@cluster.local`.
- With that admin kubeconfig, `kubectl auth can-i delete pods -A` returns `yes` (full admin).
- Node is single `control-plane,worker` and currently reports `reboot-required`.

## Phase 0: Preflight for single-node downtime risk

- Because this is a single-node control-plane + worker cluster, any reboot is full cluster downtime.
- A reboot is already pending on the host, so schedule a maintenance window before starting OpenClaw rollout.
- Confirm `kubectl` allowlist target path as `/usr/local/bin/kubectl`.

## Phase 1: Prepare host and service account

Run as `root`:

```bash
apt update
apt -y upgrade
apt -y install curl ca-certificates gnupg jq git openssl
useradd -m -s /bin/bash openclaw
loginctl enable-linger openclaw
```

Security note:

- Do not add `openclaw` to `sudo` by default. Keep it as an unprivileged service account.
- If temporary sudo is ever required for break-glass troubleshooting, grant and remove it explicitly.

Validation:

```bash
id openclaw
loginctl show-user openclaw | grep Linger
```

## Phase 2: Install OpenClaw CLI without root onboarding

Run as `root`:

```bash
curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard
```

Implementation detail used by this repo:

- `install-openclaw-host.yml` runs `https://openclaw.ai/install.sh` during initial provisioning only.
- OpenClaw itself is expected to self-manage updates after install.

Validation:

```bash
openclaw --version
```

## Phase 3: Onboard as `openclaw` with Codex OAuth

Switch user:

```bash
sudo -iu openclaw
```

Run onboarding:

```bash
openclaw onboard --install-daemon --auth-choice openai-codex
```

Wizard targets:

- Auth choice: `openai-codex`
- Primary model: `openai-codex/gpt-5.3-codex`
- Complete headless OAuth flow if callback cannot bind

Validation:

```bash
systemctl --user status openclaw-gateway
journalctl --user -u openclaw-gateway --no-pager -n 200
```

## Phase 4: Configure Telegram securely

1. Create bot token with `@BotFather` (human step).
2. Save token as `openclaw`:

```bash
umask 077
mkdir -p ~/.openclaw
cat > ~/.openclaw/.env <<'EOF'
TELEGRAM_BOT_TOKEN=PASTE_TOKEN_HERE
EOF
```

3. Set minimal hardened config in `~/.openclaw/openclaw.json`:

```json5
{
  agents: {
    defaults: {
      model: { primary: "openai-codex/gpt-5.3-codex" },
      heartbeat: { every: "0m" },
    },
  },

  channels: {
    telegram: {
      enabled: true,
      botToken: "${TELEGRAM_BOT_TOKEN}",
      dmPolicy: "pairing",
      groupPolicy: "disabled",
    },
  },

  tools: {
    deny: ["group:fs", "browser", "canvas", "nodes", "cron", "gateway"],
    elevated: { enabled: false },
  },
}
```

4. Restart and verify:

```bash
systemctl --user restart openclaw-gateway || true
journalctl --user -u openclaw-gateway --no-pager -n 200 || true
# Fallback when systemd --user is unavailable:
sudo -u openclaw sh -lc 'cd /home/openclaw && HOME=/home/openclaw openclaw gateway run'
openclaw logs --follow
```

## Phase 4a: Enable gateway on boot

Run on host:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/enable-openclaw-gateway-autostart.yml
```

Validation:

```bash
sudo systemctl status openclaw-gateway
sudo systemctl is-enabled openclaw-gateway
sudo systemctl is-active openclaw-gateway
curl --silent --max-time 2 http://127.0.0.1:18789/ | head
```

Expected:

- Unit installed at `/etc/systemd/system/openclaw-gateway.service`.
- `enabled = enabled` and `active = active`.
- Dashboard still binds loopback-only (`127.0.0.1:18789`).

## Phase 5: Pair Telegram account

From phone, DM bot once. Then as `openclaw`:

```bash
openclaw pairing list telegram
openclaw pairing approve telegram CODE_FROM_THE_LIST
```

Expected result:

- Only approved DM can control the agent.
- Groups remain disabled.

## Phase 6: Enable safe web access mode

- Keep `browser` denied.
- Use OpenClaw web tools (`web_fetch`) for public internet research.
- Keep filesystem tools denied (`group:fs`) to reduce secret exposure risk.
- Keep command execution intentionally off until phase 6b.

### Phase 6a: Optional file tool enablement

Run when you explicitly want filesystem access inside OpenClaw sessions:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/configure-openclaw-file-tool.yml
```

What this changes:

- Removes `group:fs` from `tools.deny`.
- Adds `group:fs` to `agents.main.tools.allow`.
- Restarts gateway so the session tool manifest is rebuilt.

Validation:

- `openclaw config get tools.deny` does not include `group:fs`.
- `openclaw config get agents` includes `main -> tools -> allow` with `group:fs`.

Rollback:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/disable-openclaw-file-tool.yml
```

### Phase 6b: Optional exec tooling enablement

Run when you want OpenClaw to run shell commands (`gog`, `kubectl`, etc.):

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/configure-openclaw-exec-tool.yml
```

What this changes:

- Removes `exec` from `tools.deny`.
- Adds `exec` to `agents.main.tools.allow`.
- Restarts gateway so the session tool manifest is rebuilt.

Validation:

- `openclaw config get tools.deny` does not include `exec`.
- `openclaw config get agents` includes `main -> tools -> allow` with `exec`.
- Ask OpenClaw to execute a harmless command and confirm output.

Rollback:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/disable-openclaw-exec-tool.yml
```

## Phase 6c: Enable full browser automation (explicit gate)

Run:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/configure-openclaw-full-web-browsing.yml
```

Validation:

- `openclaw config get tools.deny` should no longer include `browser`.
- `openclaw config get browser` returns enabled settings with `defaultProfile` set (typically `openclaw`).
- `openclaw browser --browser-profile openclaw status` returns a reachable status.
- OpenClaw logs should show browser control service availability.

Rollback:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/disable-openclaw-full-web-browsing.yml
```

## Phase 7: Restrict exec command allowlist for safety

Open Control UI over SSH tunnel from laptop:

```bash
ssh -L 18789:127.0.0.1:18789 openclaw@YOUR_SERVER
```

Then browse locally to `http://127.0.0.1:18789/` and configure Exec approvals:

- target: Gateway
- agent: `main`
- `security: allowlist`
- `ask: off`
- `askFallback: deny`
- `autoAllowSkills: false`
- allowlist entries: full binary path only.
  - minimum baseline: `/usr/local/bin/kubectl`
  - add `/usr/local/bin/gog` only when you want OpenClaw to run gmail CLI commands.

Validation:

- `kubectl` commands are allowed.
- `bash`, `cat`, `curl`, `env`, etc. are denied.

## Phase 8: Match OpenClaw Kubernetes permissions to node admin

Use the host admin kubeconfig as the OpenClaw identity source:

1. Ensure `openclaw` OS user exists and linger is enabled.
2. Copy `/etc/kubernetes/admin.conf` to:

```bash
/home/openclaw/.kube/config
```

Permissions:

```bash
chmod 600 /home/openclaw/.kube/config
chown openclaw:openclaw /home/openclaw/.kube/config
```

Validation:

- `KUBECONFIG=/home/openclaw/.kube/config kubectl auth can-i get pods --all-namespaces` returns yes.
- `KUBECONFIG=/home/openclaw/.kube/config kubectl auth can-i delete pods --all-namespaces` returns yes.

## Phase 9: Run security audit and apply fixes

As `openclaw`:

```bash
openclaw security audit --deep
openclaw security audit --fix
```

Post-check:

- Re-run deep audit and confirm remaining findings are understood/accepted.

## Phase 11: Rollback for autostart

- To disable boot start while keeping config and binary:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/disable-openclaw-gateway-autostart.yml
```

- To fully remove OpenClaw installation:

```bash
ansible-playbook -i kubespray/inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu \
  playbooks/operations/openclaw/remove-openclaw-host.yml
```

## Phase 10: Progressive capability expansion (one-by-one + review)

Use this when current limits are too strict and you want to add power safely.

Change-control loop (repeat for every new capability):

1. Pick exactly one capability to add.
2. Define success criteria and a rollback trigger before deployment.
3. Implement via code/config in a branch and push first.
4. Deploy only that single change.
5. Run validation checks and real-user test prompts.
6. Review logs/audit output for at least one observation window.
7. Keep or revert, then document the decision/date.

Default observation window:

- Low risk: 24 hours
- Medium/high risk: 72 hours

Rollback rule:

- If unexpected behavior appears, revert the last single capability change only.

### Expansion ladder (recommended order)

#### Step 10.1: Reduce Kubernetes permissions later (if desired)

- Keep exec restricted to `/usr/local/bin/kubectl`.
- Add only required new verbs/resources for one namespace/app at a time.
- Validate both allow and deny behavior:
  - `KUBECONFIG=/home/openclaw/.kube/config kubectl auth can-i <verb> <resource> -n <allowed-ns>`
  - `KUBECONFIG=/home/openclaw/.kube/config kubectl auth can-i <verb> <resource> -n kube-system`

#### Step 10.2: Add one more host binary (if needed)

- Add one explicit binary path in Exec approvals allowlist (for example `helm`), not a wildcard.
- Verify that only the new binary is added and all other binaries remain denied.

#### Step 10.3: Relax Telegram policy incrementally

- Keep DMs in `pairing`.
- If group support is needed later, enable only for explicit approved chats and test with a non-approved chat first.

#### Step 10.4: Relax tool denies incrementally

- Remove one denied tool at a time from `tools.deny`.
- Test that the new tool works and that previous guardrails still hold.
- Keep `tools.elevated.enabled: false` unless there is a strict break-glass need.

#### Step 10.5: Enable heartbeat last

- Change from `0m` to a conservative interval only after prior steps are stable.
- Review behavior for noisy/unexpected proactive actions before reducing interval further.

### Review checklist per step

- No new secrets exposed in logs or chat.
- No unapproved command paths executed.
- Kubernetes actions match intended cluster access profile.
- Telegram access scope matches intended policy.
- `openclaw security audit --deep` remains clean or deviations are accepted and documented.

## Phase 12: Gmail webhooks saga (post-installation)

This is the exact saga from the current cluster install. Keep this as the reference
when re-running Gmail webhooks on the same node.

### What happened (in order)

- Initial `openclaw webhooks gmail setup` worked only after:
  - installing `gcloud`
  - selecting a project with Mail/PubSub enabled
  - passing `--project <PROJECT_ID>` consistently.
- OAuth setup initially failed with:
  - missing OAuth credentials JSON
  - malformed/unfinished redirect URL handling from the terminal
  - “access_denied” on Google verification/testing state.
- Final successful run required:
  - keyring passphrase supplied on each run
  - clean redirect URL passed to `gog auth add ... --remote --step 2`
  - `tailscale` DNS/funnel enabled for a reachable push endpoint.

Observed values in this deployment:

- account: `kpoxo6op@gmail.com`
- project: `kpoxo6op`
- OAuth client: Desktop app JSON at `~/.config/gogcli/credentials.json` for `openclaw` user
- hooks topic: `projects/kpoxo6op/topics/gog-gmail-watch`
- hooks subscription: `gog-gmail-watch-push`

### What worked for this deployment

Use this pattern for rerun or audits (replace placeholders only):

1. Configure project and API enablement once:

```bash
gcloud config set project <PROJECT_ID>
gcloud --project=<PROJECT_ID> services enable gmail.googleapis.com pubsub.googleapis.com
```

2. Ensure OAuth creds file exists for gog:

```bash
sudo -u openclaw mkdir -p /home/openclaw/.config/gogcli
sudo -u openclaw test -f /home/openclaw/.config/gogcli/credentials.json
```

3. Start auth step 1 (as openclaw with keyring passphrase):

```bash
sudo -u openclaw GOG_KEYRING_PASSWORD='<KEYRING_PASS>' \
  bash -lc 'gog auth add <user@gmail.com> --services gmail --remote --step 1'
```

4. Open the returned URL, authenticate, then pass the full redirect URL exactly once:

```bash
AUTH_URL='<FULL_REDIRECT_URL>'
AUTH_URL=$(printf "%s" "$AUTH_URL" | tr -d "\r\n")
sudo -u openclaw GOG_KEYRING_PASSWORD='<KEYRING_PASS>' \
  bash -lc 'gog auth add <user@gmail.com> --services gmail --remote --step 2 --auth-url "$AUTH_URL"'
```

5. Verify token record exists:

```bash
sudo -u openclaw GOG_KEYRING_PASSWORD='<KEYRING_PASS>' bash -lc 'gog auth list'
```

6. Setup OpenClaw Gmail webhooks:

```bash
sudo -u openclaw GOG_KEYRING_PASSWORD='<KEYRING_PASS>' \
  openclaw webhooks gmail setup --account <user@gmail.com> --project <PROJECT_ID>
```

7. Start watch loop:

```bash
sudo -u openclaw GOG_KEYRING_PASSWORD='<KEYRING_PASS>' openclaw webhooks gmail run
```

### Post-checks to confirm final health

- `openclaw config get hooks`
  - `hooks.enabled: true`
  - `hooks.presets` contains `"gmail"`
  - `hooks.gmail.account` matches `<user@gmail.com>`
  - `hooks.gmail.topic` and `hooks.gmail.subscription` are set.
- `gog gmail watch serve` reports local listener on `127.0.0.1:8788`.
- `gog gmail watch status --account <user@gmail.com> --json` returns valid history data.
- `gcloud --project=<PROJECT_ID> pubsub subscriptions describe <subscription>` returns `state: ACTIVE`.
- `openclaw webhooks gmail status` (if available in your installed version) returns configured state.

### What to do if it fails again

- `Error: No tokens stored`: rerun step 1/2 with correct keyring passphrase.
- `Error: GCP project id required`: add `--project` and verify `gcloud config set project`.
- `Error: push endpoint required` or `tailscale DNS name missing`: confirm node is on tailscale and funnel/DNS route is reachable.
- Webhook auth URL looks broken by terminal wrapping: copy/paste with no newlines, then run `tr -d "\r\n"`.

## Operational checklist

- Gateway runs as `openclaw` with linger enabled.
- OAuth, pairing, and credential files in `~/.openclaw/` treated as secrets.
- `~/.openclaw/` and `.env` are never committed to git.
- Telegram remains `dmPolicy: pairing` and `groupPolicy: disabled`.
- Heartbeat remains disabled (`0m`) until trust level increases.
- Gateway UI is not exposed publicly.
- Exec approvals remain allowlist-only.

## References

- [Gateway runbook](https://docs.openclaw.ai/gateway)
- [Installer](https://docs.openclaw.ai/install/installer)
- [OpenAI provider](https://docs.openclaw.ai/providers/openai)
- [OAuth](https://docs.openclaw.ai/concepts/oauth)
- [Telegram channel](https://docs.openclaw.ai/channels/telegram)
- [Gateway configuration](https://docs.openclaw.ai/gateway/configuration)
- [Tools overview](https://docs.openclaw.ai/tools)
- [Heartbeat](https://docs.openclaw.ai/gateway/heartbeat)
- [Logging](https://docs.openclaw.ai/logging)
- [Pairing](https://docs.openclaw.ai/pairing)
- [Web tools](https://docs.openclaw.ai/tools/web)
- [Exec approvals](https://docs.openclaw.ai/tools/exec-approvals)
- [Control UI](https://docs.openclaw.ai/index)
- [Security audit](https://docs.openclaw.ai/gateway/security)
- [Agent workspace guidance](https://docs.openclaw.ai/agent-workspace)
- `soydocs/openclaw-node0-ops-checklist.md` — node-0 one-page operational checklist for Gmail/webhooks/browser health.
