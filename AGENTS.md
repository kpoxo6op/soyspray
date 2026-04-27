# AGENTS.md

## Project Overview
This repo manages a kubespray-provisioned Kubernetes cluster and its workloads
(Ansible + Argo CD apps). Work often includes cluster operations, logs/alerts,
and backup/retention checks.

## Tools
- `kubectl`: Inspect cluster resources, pods, logs, and CRs.
- `aws` CLI: Check backup objects and IAM policies/permissions when S3 is
  involved.
- `gh` (GitHub CLI): Create/merge PRs and update PR descriptions.
- `ansible-playbook`: Run runbooks with the repo’s inventory and standard
  privilege escalation; check `Makefile` targets for canonical command
  templates.

## Node Access
- Use `make master` (SSH) to access the single Kubernetes node.
- The node IP is `192.168.20.10` and the SSH user is `ubuntu` (per `Makefile`).

## Networking Notes
- Router (OpenWrt) is at `192.168.20.1`.
- LAN subnet: `192.168.20.0/24`.
- DNS override: `soyspray.vip` resolves to `192.168.20.20` via router dnsmasq.
- Tailscale on the router advertises the LAN route `192.168.20.0/24` and forwards
  `tailscale -> lan`.

## Workflow
- Never run impertive commands modifying the cluster. Make changes in code.
- Never modify `main` directly. Always work in a branch (PR branch or local
  topic branch) and keep `main` untouched. Exception: markdown and comments.
- For PR work: check out the PR branch, make changes there, push, then deploy.
- Push changes to the remote before running any deploys or cluster actions.
- Run `make go` before deploying changes (humans can run this interactively).
- Activate the venv via `make act` before running Ansible.
- For non-interactive runs, use:
  `source soyspray-venv/bin/activate && ansible-playbook ...`.
- When deploying a branch before merge, temporarily point the Argo app
  `targetRevision` at that branch, then revert to `HEAD` after merge.
- When creating PRs, ensure any temporary Argo `targetRevision` changes are
  set back to `HEAD`.
- Prefer explicit confirmations before destructive cluster actions.

## OpenClaw
- Keep the browser on direct OpenClaw control only (no Chrome extension relay).
- Known issue this session: browser control failed due bad Chrome path resolution; enforce
  `browser.executablePath=/usr/bin/google-chrome-stable` in config.
- Auth is OAuth-only (`openai-codex`) moving forward (use your ChatGPT subscription flow).
- Do not store OpenAI API keys or static provider tokens in repo or checked-in configs.
- Re-run OAuth when auth is broken:
  - `sudo su - openclaw -c "openclaw onboard --auth-choice openai-codex --set-default"`
  - or `sudo su - openclaw -c "openclaw models auth login --provider openai-codex --method oauth --set-default"`
- After OAuth, verify quickly:
  - `sudo su - openclaw -c "openclaw models auth list"`
  - `sudo su - openclaw -c "openclaw models status"`
- Non-interactive OAuth token refresh:
  - Set `OPENCLAW_OAUTH_ACCESS_TOKEN='<access-token>'` (required), optional
    `OPENCLAW_OAUTH_REFRESH_TOKEN='<refresh-token>'`, optional `OPENCLAW_OAUTH_EXPIRES_IN='30d'`.
  - Run: `ansible-playbook playbooks/operations/openclaw/configure-openclaw-oauth-token.yml`
- Re-extract fresh token after interactive OAuth flow:
  - `sudo su - openclaw -c "jq -r '.profiles[\"openai-codex:default\"].access' ~/.openclaw/agents/main/agent/auth-profiles.json"`
- If browser automation fails:
  - `sudo su - openclaw -c "openclaw browser status --browser-profile openclaw2 --json"`
  - `sudo su - openclaw -c "openclaw browser stop --browser-profile openclaw2"`
  - `sudo su - openclaw -c "openclaw browser start --browser-profile openclaw2"`
  - `sudo su - openclaw -c "openclaw browser --json status --browser-profile openclaw2"`
- Service checks after restart:
  - `sudo su - openclaw -c "openclaw gateway status --json"`
  - `sudo su - openclaw -c "openclaw health"`
- Keep stable config targets in `~/.openclaw/openclaw.json`:
  - `gateway.auth.mode=token`, `gateway.auth.token` present
  - `browser.executablePath=/usr/bin/google-chrome-stable`
  - `browser.profiles.openclaw2.cdpPort` expected to stay stable
- If jobs fail after service restart, rerun one-off job before changing anything else:
  - `openclaw runjob once openclaw2`
