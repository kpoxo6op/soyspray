# Repository tests

The test suite checks repository behavior and deployment rules without
requiring a live cluster.

| File | Coverage |
| --- | --- |
| [`test_agent_secret.py`](test_agent_secret.py) | Vaultwarden reader allow-list, error handling, locking, and repeated reads |
| [`test_hays_open_submitted_timesheet.py`](test_hays_open_submitted_timesheet.py) | Safe proof and credential boundary for the submitted-timesheet opener |
| [`test_api_contracts.py`](test_api_contracts.py) | OpenAPI contracts and API catalog consistency |
| [`test_customer_app.py`](test_customer_app.py) | Demo server and browser-facing responses |
| [`test_docs.py`](test_docs.py) | Operator documentation and links |
| [`test_gitops.py`](test_gitops.py) | Argo CD ownership and lifecycle rules |
| [`test_live_tv.py`](test_live_tv.py) | Live TV catalog, Jellyfin guide, playback services, SSO, and lifecycle contracts |
| [`test_render.py`](test_render.py) | Kustomize rendering and manifest expectations |
| [`test_repo_quality.py`](test_repo_quality.py) | Repository structure and reusable skills |
| [`test_runtime_tools.py`](test_runtime_tools.py) | Status and smoke command behaviour |
| [`test_security.py`](test_security.py) | Network and gateway security controls |
| [`test_sso.py`](test_sso.py) | Authentik secrets, base blueprints, and recovery access |
| [`test_sso_headlamp.py`](test_sso_headlamp.py) | Headlamp OIDC and Authentik secret-change rollout |
| [`test_sso_legacy_proxy.py`](test_sso_legacy_proxy.py) | Authentik forward auth and machine API exceptions |
| [`test_sso_native_apps.py`](test_sso_native_apps.py) | Native application OIDC clients and access groups |
| [`test_vaultwarden_deployment.py`](test_vaultwarden_deployment.py) | Vaultwarden manifests, Argo CD ownership, and role lifecycle |

[`conftest.py`](conftest.py) provides shared paths and manifest helpers. Run the
focused suite with `make test`, or the complete local gate with `make check`.
