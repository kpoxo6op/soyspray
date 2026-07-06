# Kong Argo CD Templates

These Application manifests plug goal 002 into the goal 001 app-of-apps layout.
They are templates until `REPLACE_WITH_REPO_URL` is replaced with the real repo.

Sync order:

1. Gateway API and Kong baseline.
2. Smoke backend and routes.
3. Static and cluster smoke checks outside Argo CD.

Rollback should be a Git revert or an Argo CD sync to the previous commit. Do
not repair drift with direct kubectl edits.
