# Media Recovery Test 2

Restore the reviewed Immich manifests through the normal release path: merge
the change to `main`, then wait for the native Argo root and Immich Application
to become `Synced` and `Healthy`.

```bash
make status APP=immich FORMAT=json
```

Immich app failing - empty PVC missing `.immich` marker files. Restore media from S3:

```bash
kubectl run -n immich restore-media \
  --image=public.ecr.aws/aws-cli/aws-cli:latest \
  --rm -it --restart=Never \
  --overrides='{
    "spec": {
      "securityContext": {"runAsUser": 0, "runAsGroup": 0},
      "containers": [{
        "name": "restore",
        "image": "public.ecr.aws/aws-cli/aws-cli:latest",
        "command": ["sh", "-c", "aws s3 sync s3://immich-offsite-archive-au2/immich/media/ /library/"],
        "envFrom": [{"secretRef": {"name": "immich-offsite-writer"}}],
        "volumeMounts": [{"name": "library", "mountPath": "/library"}]
      }],
      "volumes": [{"name": "library", "persistentVolumeClaim": {"claimName": "immich-library"}}]
    }
  }' -- /bin/true
```

Media restored (102 files, 91.6 MiB). Immich still failing - missing generated content folders. Create them:

```bash
kubectl run -n immich create-missing-folders \
  --image=busybox --rm -it --restart=Never \
  --overrides='{
    "spec": {
      "securityContext": {"runAsUser": 0, "runAsGroup": 0},
      "containers": [{
        "name": "init",
        "image": "busybox",
        "command": ["sh", "-c", "mkdir -p /library/thumbs /library/encoded-video /library/backups && touch /library/thumbs/.immich /library/encoded-video/.immich /library/backups/.immich && ls -la /library"],
        "volumeMounts": [{"name": "library", "mountPath": "/library"}]
      }],
      "volumes": [{"name": "library", "persistentVolumeClaim": {"claimName": "immich-library"}}]
    }
  }' -- /bin/true
```

Immich healthy. Thumbnails missing (98% failed) - generated content not backed up. Regenerate via Immich Admin UI Jobs. Drill complete.
