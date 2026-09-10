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
| Headlamp | Authenticated view of Kubernetes resources | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/headlamp) |
| OpenCode Remote | Private phone access to OpenCode running on laptop `mox` | [Application folder](https://github.com/kpoxo6op/soyspray/tree/main/apps/opencode-remote) |
| Monitoring | Metrics, alerts, logs, and public service status | [Application folders](https://github.com/kpoxo6op/soyspray/tree/main/apps) |

Use the repository's native application catalogue when you need the complete
current list:

```sh
make apps
```
