# Prometheus, AlertManager, and Telegram Integration

## Architecture

```text
                                                    ┌─────────────────┐
                                                    │                 │
                                                    │  Telegram Bot   │
                                                    │                 │
                                                    └────────▲────────┘
                                                            │
                                                            │
┌──────────────┐         ┌──────────────┐         ┌────────┴────────┐
│              │         │              │         │                 │
│  Prometheus  ├────────►│ AlertManager ├────────►│ Secret:        │
│              │  Alert  │              │   Uses  │ bot_token      │
└──────┬───────┘         └──────────────┘         │                 │
       │                                          └─────────────────┘
       │
       │ Evaluates
       ▼
┌──────────────┐
│ PrometheusRules:
│ - temperature│
│ - other      │
└──────────────┘
```

## Components Overview

### 1. Prometheus Rules

- Located in `alerts/` directory
- Each rule file defines conditions for specific alerts
- Example rules:
  - Temperature monitoring
  - Node status
  - Application metrics

### 2. AlertManager Configuration (values.yaml)

```yaml
alertmanager:
  config:
    route:
      receiver: 'telegram'
      routes:
        - matchers:
          - severity=~"warning|critical"
    receivers:
    - name: 'telegram'
      telegram_configs:
      - bot_token_file: /etc/alertmanager/telegram/TELEGRAM_BOT_TOKEN
        chat_id: 336642153
```

### 3. Telegram Integration (managed by Ansible)

- Bot token stored in .env file
- Ansible creates secret: `alertmanager-telegram-secret`
- Mounted in AlertManager pod

## Flow

1. Prometheus continuously evaluates alert rules
2. When any rule triggers, alert sent to AlertManager
3. AlertManager routes based on severity/labels
4. Notifications sent to Telegram via bot

## Adding New Alerts

1. Create new rule file in `alerts/` directory
2. Add appropriate labels for routing
3. Update kustomization.yaml if needed
4. Test with temporary thresholds

## Maintenance

- Alert rules managed in individual yaml files
- Bot credentials through .env and Ansible
- AlertManager config in values.yaml

## Verification

- Prometheus UI: `/alerts`
- AlertManager: `/alertmanager/config`
- Test new rules by lowering thresholds
