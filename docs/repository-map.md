# Repository map

| Path | Purpose |
| --- | --- |
| `.agents/skills` | Reusable review, testing, GitOps, Ansible, security, and demo UX workflows |
| `apis/synthetic-bank` | Mock APIs, OpenAPI files, routes, and the API catalog |
| `kubernetes/banklab` | Customer app, docs site, traffic clients, security, and governance |
| `platform/kong` | Kong release values, Gateway API, smoke service, and policies |
| `playbooks/argocd/applications/kong-bank-lab` | Argo projects and Applications |
| `roles/apps/kong-bank-lab` | Idempotent start and stop lifecycle plus runtime-only credentials |
| `tests` | Local manifest, policy, and application tests |
| `docs` | Operator documentation source |
| `soydocs` | Cluster history and one-off maintenance notes |

Generated build output belongs under `.build`. Runtime reports should come from
repeatable commands and dashboards, not checked-in snapshots that go stale.
