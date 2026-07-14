# Repository tests

The test suite checks the Kong lab without requiring a live cluster.

| File | Coverage |
| --- | --- |
| [`test_api_contracts.py`](test_api_contracts.py) | OpenAPI contracts and API catalog consistency |
| [`test_customer_app.py`](test_customer_app.py) | Demo server and browser-facing responses |
| [`test_docs.py`](test_docs.py) | Operator documentation and links |
| [`test_gitops.py`](test_gitops.py) | Argo CD ownership and lifecycle rules |
| [`test_render.py`](test_render.py) | Kustomize rendering and manifest expectations |
| [`test_repo_quality.py`](test_repo_quality.py) | Repository structure and reusable skills |
| [`test_runtime_tools.py`](test_runtime_tools.py) | Status and smoke command behaviour |
| [`test_security.py`](test_security.py) | Network and gateway security controls |

[`conftest.py`](conftest.py) provides shared paths and manifest helpers. Run the
focused suite with `make test`, or the complete local gate with `make check`.
