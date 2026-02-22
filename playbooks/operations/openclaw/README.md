# OpenClaw Operations

Runbooks for OpenClaw installation, runtime control, and Gmail/webhook integration.

## Canonical entrypoints

- `openclaw-install.yml` - one-command bootstrap: preflight → host/dependency install → baseline config → kubeconfig → enable gateway boot-start → final status
- `openclaw-remove.yml` - one-command teardown: disable boot-start → remove install-mode config → remove kubeconfig → remove dependencies → remove host/user and service
- `openclaw-enable-tools.yml` - enable optional tool capabilities in one pass (`file`, `exec`, `browser`)
- `openclaw-disable-tools.yml` - disable optional tool capabilities in one pass (`browser`, `exec`, `file`)

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
