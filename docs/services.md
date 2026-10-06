# Services

Each application keeps its manifests, checks, recovery code, and technical
README in its own repository folder. This page is the human entry point; the
application folder is authoritative for commands and limits.

| Area | What it provides | Technical details |
| --- | --- | --- |
| Home Assistant | Home controls, devices, and voice-assistant integration | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/home-assistant) |
| Immich | Personal photo library and its database recovery path | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/immich) |
| Jellyfin | Local films, television, and live-TV playback | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/jellyfin) |
| Vaultwarden | Personal password vault and restricted automation access | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/vaultwarden) |
| Obsidian LiveSync | Synchronisation for the personal Obsidian vault | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/obsidian-livesync) |
| Boys | Shared trip calendar and accommodation links | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/boys) |
| Autism traits assessment | Public bilingual assessment; runtime changes use a reviewed image promotion | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/autism-traits) |
| Headlamp | Authenticated view of Kubernetes resources | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/headlamp) |
| DeepSeek Harness Remote | Authentik-protected phone access to the official DeepSeek Harness running on laptop `mox` at `ai.soyspray.vip` | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/ai) |
| GI private workspace | Single-user private workspace at `gi.soyspray.vip`, restricted to the `gi-users` group, with its own claims and forward-auth route | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/gi) |
| Monitoring | Metrics, alerts, logs, and public service status | [Application folders](https://github.com/kpoxo6op/soyspray/tree/main/apps) |

Use the repository's native application catalogue when you need the complete
current list:

```sh
make apps
```

Home Assistant supports the Fellow Stagg EKG Pro through a pinned unofficial
local Wi-Fi integration. Pair Wi-Fi in Fellow's app, then add the integration
in Home Assistant. It does not measure water quantity or automatically create
heating schedules. Keep its unauthenticated local interface on the trusted
LAN. Setup, firmware limits, checks, and rollback are documented in the
[Home Assistant README](https://github.com/kpoxo6op/soyspray/tree/main/apps/home-assistant).

Local Voice uses Speech-to-Phrase's native input gain to help quiet microphone
audio reach speech recognition. The GI wake detector retains its own settings.
Use the [Voice guide](https://github.com/kpoxo6op/soyspray/tree/main/apps/voice-assistant)
for transport checks and physical microphone verification; a wake flash alone
does not prove a recognized command.
