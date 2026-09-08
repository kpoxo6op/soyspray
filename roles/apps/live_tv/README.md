# Live TV input role

This role creates and preserves the Dispatcharr and Jellyfin runtime Secrets.
It does not submit Applications and it does not select a Git revision. Argo CD
owns both workloads from the catalog.

```sh
make -f apps/live-tv/Makefile bootstrap
```

Stopping or retiring live TV is a separate deliberate operation. Bootstrap
does not delete workloads, claims, or shared media files.
