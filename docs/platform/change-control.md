# Goal005 Change Control

Goal005 uses Git as the source of truth for API platform changes. Runtime
changes must be represented by committed manifests or committed renderers before
they are applied.

## Change Classes

`standard` changes are preapproved catalog or metadata changes with local
validation evidence.

`normal` changes require tenant and platform review, local rendered-manifest
validation, runtime smoke evidence, and rollback evidence.

`emergency` changes require break-glass approval, runtime smoke, rollback
evidence, and retrospective review.

`security` changes require security and platform review, runtime smoke,
rollback evidence, and explicit security review evidence.

## Evidence Expectations

Each change must identify the tenant, API product, affected resources, expected
runtime evidence, rollback command, and approver placeholders. Runtime evidence
must avoid credential values and must preserve the Kong Admin API exposure
boundary.

## Sample Goal005 Change

The sample normal change adds a temporary response header to the `accounts`
API through a namespaced Kong `response-transformer` plugin and an HTTPRoute
annotation update. The rollout smoke proves the header is visible. The rollback
smoke removes only that plugin, restores the route annotation, and proves
goal004 authentication, authorization, correlation ID, and rate-limit behavior
still work.
