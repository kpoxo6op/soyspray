# OpenClaw Operations

Runbooks for OpenClaw installation, runtime control, and Gmail/webhook integration.

## Canonical entrypoints

- `openclaw-install.yml` - one-command bootstrap: preflight → host/dependency install → baseline config → kubeconfig → enable gateway boot-start → final status
- `openclaw-remove.yml` - one-command teardown: disable boot-start → remove install-mode config → remove kubeconfig → remove dependencies → remove host/user and service
- `openclaw-enable-tools.yml` - enable optional tool capabilities in one pass (`file`, `web search`, `exec`, `browser`)
- `openclaw-disable-tools.yml` - disable optional tool capabilities in one pass (`browser`, `web search`, `exec`, `file`)

Use tags to narrow a tool pass:

- `-t openclaw-tools-file` for `group:fs`
- `-t openclaw-tools-web` for `web_fetch` and `web_search` via Brave
- `-t openclaw-tools-exec` for `exec`
- `-t openclaw-tools-browser` for `browser`/Playwright stack

## Legacy one-purpose playbooks

Kept for direct targeting and rollback scripting:

- `audit-openclaw-security.yml`
- `configure-openclaw-exec-tool.yml`
- `configure-openclaw-file-tool.yml`
- `configure-openclaw-web-search.yml`
- `configure-openclaw-full-web-browsing.yml`
- `configure-openclaw-installation-mode.yml`
- `configure-openclaw-kubeconfig.yml`
- `disable-openclaw-exec-tool.yml`
- `disable-openclaw-file-tool.yml`
- `disable-openclaw-web-search.yml`
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

## Web Search

Use `configure-openclaw-web-search.yml` to enable OpenClaw's native `web_search`
and `web_fetch` tools. The runbook expects `BRAVE_API_KEY` in the shell
environment, writes it to `~openclaw/.openclaw/.env`, enables:

- `tools.web.fetch.enabled: true`
- `tools.web.search.enabled: true`
- `tools.web.search.provider: brave`

It also adds `web_fetch` and `web_search` to the main agent allowlist so the
agent can stop falling back to browser scraping for simple listing research.
