# Kong bank lab role tasks

The role task flow is intentionally split by lifecycle phase.

| File | Purpose |
| --- | --- |
| [`main.yml`](main.yml) | Chooses the enabled or disabled path |
| [`project.yml`](project.yml) | Keeps the Argo project and Kong CRDs present |
| [`enabled.yml`](enabled.yml) | Applies runtime applications and creates missing demo credentials |
| [`disabled.yml`](disabled.yml) | Stops automated sync, then removes runtime applications in reverse order |

Generated credentials are marked `no_log` and are never written to the
repository.
