# Plex

Argo CD app for Plex Media Server.

## Validating Preferences

1. After the pod starts, inspect the applied preferences:
   ```bash
   kubectl exec -n media deploy/plex -- cat \
     "/config/Library/Application Support/Plex Media Server/Preferences.xml"
   ```
   Ensure attributes like `PublishServerOnPlexOnlineKey="0"`,
   `GdmEnabled="0"`, `RelayEnabled="0"`, `SendCrashReports="0"`, and
   `FirstRun="0"` are present.
2. Check the Plex log for warnings about unknown preferences:
   ```bash
   kubectl logs -n media deploy/plex | grep -i preference
   ```
   Absence of warnings indicates Plex recognized the settings.
