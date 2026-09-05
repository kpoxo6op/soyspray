# Live TV role

This role creates runtime secrets and applies the Dispatcharr and Jellyfin Argo CD Applications.

Set `live_tv_enabled=true` to start the applications. Set it to `false` to stop workloads without deleting claims.

- [Defaults](defaults/README.md)
- [Tasks](tasks/README.md)

The native root owns Media Helper. Use `make deploy APP=media-helper` for it.
