# Plex: Deployment Debug & Validation Guide

End-to-end validation guide for stateless, offline Plex with auto-bootstrapped TV library (Personal/None agent). Includes exact commands, expected outputs, and quick fixes. Designed for ArgoCD-driven deploys with linuxserver/plex:1.41.3 and Sonarr's organized PVC mounted read-only.

## What the deployment does

1. **Seeds offline Preferences.xml** into `/config/Library/Application Support/Plex Media Server/`.
2. **Creates a TV Shows library** using the Personal Media Shows agent (`com.plexapp.agents.none`) that performs no online metadata lookups.
3. **Scans `/data`** (the read‑only mount of the `sonarr-tv` PVC) so Twin Peaks appears immediately.
4. **Runs stateless** with `emptyDir` at `/config`, re-seeding on every Pod start.

## One‑time prerequisites

- `kubectl` context points at the cluster that runs ArgoCD.
- The `media` namespace exists or is created by ArgoCD.

## 1) Confirm the Pod is up

```bash
kubectl get pods -n media -l app=plex
```

**Expected output:**
```
NAME                    READY   STATUS    RESTARTS   AGE
plex-7c8b9d4f6d-xyz12   1/1     Running   0          2m
```

**If PENDING:** Check PVC availability:
```bash
kubectl get pvc -n media sonarr-tv
```

**If CrashLoopBackOff:** Check init container logs:
```bash
kubectl logs -n media deployment/plex -c bootstrap
```

## 2) Verify bootstrap script execution

Check the init container completed successfully:

```bash
kubectl logs -n media deployment/plex -c bootstrap
```

**Expected output:**
```
Setting up Plex configuration directory...
Creating TV Shows library with Personal Media Shows agent...
Scanning TV Shows library...
Created library sections:
1: TV Shows
Bootstrap complete - Plex ready for offline operation with TV library
```

**If missing "TV Shows" library:** The Plex Media Scanner may not be available in the linuxserver image. Check main container logs for startup errors.

## 3) Verify offline preferences are loaded

```bash
kubectl exec -n media deployment/plex -- cat "/config/Library/Application Support/Plex Media Server/Preferences.xml"
```

**Expected output (key settings):**
```xml
<Preferences
  enableLocalSecurity="0"
  allowedNetworks="192.168.0.0/255.255.0.0,10.0.0.0/255.0.0.0,172.16.0.0/255.240.0.0,fd00::/8"
  PublishServerOnPlexOnlineKey="0"
  ...
/>
```

**If file missing:** Check that init container mounted volumes correctly and bootstrap script ran.

## 4) Check Sonarr TV content is accessible

Verify Plex can see the Sonarr-organized TV shows:

```bash
kubectl exec -n media deployment/plex -- ls -la /data/
```

**Expected output (example):**
```
drwxr-xr-x    3 1000     1000          4096 Dec 15 10:30 .
drwxr-xr-x    1 root     root          4096 Dec 15 10:25 ..
drwxr-xr-x    4 1000     1000          4096 Dec 15 10:30 Twin Peaks (1990)
drwxr-xr-x    3 1000     1000          4096 Dec 15 10:29 Other TV Show
```

**If empty:** Check that `sonarr-tv` PVC is properly mounted and contains organized content from Sonarr.

## 5) Access Plex web interface

Get the service endpoint:

```bash
# If using ingress
kubectl get ingress -n media plex

# If using NodePort/LoadBalancer
kubectl get svc -n media plex
```

Navigate to the Plex URL and verify:

- **No sign-in required** (due to `enableLocalSecurity="0"`)
- **TV Shows library exists** and shows "Personal Media Shows" as agent
- **Twin Peaks appears** in the library without metadata (title only)

## 6) Verify stateless operation

Restart the pod and confirm it rebuilds correctly:

```bash
kubectl rollout restart deployment/plex -n media
kubectl get pods -n media -l app=plex -w
```

Wait for new pod to be `Running`, then repeat steps 2-5. Everything should rebuild identically.

## Common issues & fixes

### Init container fails with "Plex Media Scanner not found"

The linuxserver image may not include the CLI scanner in the expected location.

**Fix:** Update bootstrap script to skip library creation and create manually via web UI:

```bash
# Remove/comment out the scanner commands in bootstrap-configmap.yaml:
# "/usr/lib/plexmediaserver/Plex Media Scanner" --add-section...
# "/usr/lib/plexmediaserver/Plex Media Scanner" --scan
```

Then create the TV library manually pointing to `/data` with "Personal Media Shows" agent.

### TV Shows library created but Twin Peaks not detected

Check Sonarr's naming convention matches Plex expectations:

```bash
kubectl exec -n media deployment/plex -- find /data -name "*Twin*" -type f
```

**Expected structure:**
```
/data/Twin Peaks (1990)/Season 01/Twin Peaks - S01E01 - Episode Name.mkv
```

### Preferences not applied (Plex asks for sign-in)

Verify environment variable is set correctly:

```bash
kubectl exec -n media deployment/plex -- env | grep PLEX_MEDIA
```

**Expected:**
```
PLEX_MEDIA_SERVER_APPLICATION_SUPPORT_DIR=/config/Library/Application Support
```

### PVC mount issues

Check PVC is bound and accessible:

```bash
kubectl describe pvc -n media sonarr-tv
kubectl get pv
```

Ensure the PVC is `Bound` and the underlying storage is healthy.

## Quick validation checklist

- [ ] Pod is `Running` (not `CrashLoopBackOff` or `Pending`)
- [ ] Bootstrap logs show "Bootstrap complete"
- [ ] Preferences.xml exists with offline settings
- [ ] `/data` contains TV shows from Sonarr
- [ ] Web UI accessible without sign-in
- [ ] TV Shows library exists with Personal Media Shows agent
- [ ] Twin Peaks visible in library
- [ ] Restart rebuilds everything correctly (stateless)

## ArgoCD sync commands

```bash
# Deploy/update Plex
argocd app sync plex

# Check deployment status
argocd app get plex

# Force refresh if needed
argocd app refresh plex
```

## Rollback procedure

If deployment fails, rollback via ArgoCD:

```bash
# Get previous revision
argocd app history plex

# Rollback to specific revision
argocd app rollback plex <revision-id>
```

Or revert Git changes and re-sync:

```bash
git revert <commit-hash>
git push
argocd app sync plex
```
