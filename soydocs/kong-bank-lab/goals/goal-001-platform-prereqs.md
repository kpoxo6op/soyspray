# goal-001-platform-prereqs

Source: requested from ChatGPT Pro on 2026-07-06 after reporting the completed
`goal-000-repo-foundation` implementation and asking for feedback plus the next
goal with corrections folded into goal 001.

## Feedback on goal-000

Based on the implementation report, goal 000 appears to have delivered the
intended repository foundation and local validation gate.

Positive findings to preserve:

- Repository foundation was implemented rather than only documented.
- Local validation was run successfully with:

```bash
make validate && make test && make policy-test && make docs && make evidence
```

- Evidence report exists at:

```text
reports/goal-000-summary.md
```

- Goal 000 correctly performed no cluster changes.
- Goal 000 correctly created no secrets.
- Goal 000 correctly used no Kong Enterprise features.
- Secret-hygiene corrections were made for existing Booklore and Immich
  default/plain DB secret values.
- Repo-wide validation was strengthened to detect obvious plaintext/default
  secret markers and kubeconfig-like content.
- Existing Kubespray submodule examples are excluded from inappropriate secret
  scanning.

Items to verify or tighten during goal 001:

- Confirm `CHANGE_ME_WITH_NON_REPO_SECRET` placeholders are treated as
  intentional placeholders, not valid deployable secrets.
- Confirm no generated platform prerequisite manifests contain real
  credentials, kubeconfigs, private keys, API tokens, or reusable passwords.
- Confirm validation scripts fail if platform prerequisite manifests
  accidentally introduce deployable default secrets.
- Confirm `reports/goal-000-summary.md` remains historically accurate after
  goal 001 changes.
- Confirm archived planning docs under `soydocs/kong-bank-lab/` and
  `goals/goal-000-repo-foundation.md` do not become sources of truth that
  conflict with the root `ROADMAP.md`, `docs/architecture/*`, or active goal
  files.
- Confirm all new goal 001 files follow the same repo conventions, evidence
  model, and "nothing deployed without tests" rule created in goal 000.

## Objective

Implement the Kubernetes platform prerequisite layer for the Kong OSS bank-lab
before installing Kong.

This goal must define and test the base Kubernetes platform structure that
future Kong installation work will depend on. It must prepare namespaces,
GitOps layout, Argo CD app-of-apps structure, MetalLB structure, cert-manager
structure, SOPS/age secret-management structure, baseline NetworkPolicy,
validation commands, cluster-smoke commands, documentation, and evidence
reporting.

This goal must stay strictly before Kong Gateway installation.

The result should be a bank-like platform prerequisite layer that is:

- GitOps-friendly.
- Reviewable through pull requests.
- Namespace-oriented.
- Policy-aware.
- Safe by default.
- Suitable for a 3-node home Kubernetes cluster.
- Explicit about ownership and rollback.
- Testable locally before cluster use.
- Testable against a cluster when the user chooses to apply it.

The goal must create deployable or clearly staged prerequisite manifests, but it
must not deploy Kong, configure Kong, or create any Kong Gateway resources.

## Non-goals

- Do not install Kong Gateway.
- Do not install Kong Ingress Controller.
- Do not install Kong Gateway Operator.
- Do not create Kong `GatewayClass`, `Gateway`, `HTTPRoute`, `KongPlugin`,
  `KongClusterPlugin`, `KongConsumer`, `KongIngress`, `TCPIngress`,
  `UDPIngress`, or any other Kong-specific runtime resource.
- Do not expose a Kong Admin API.
- Do not create synthetic banking APIs yet.
- Do not create API consumers yet.
- Do not implement API authentication, authorization, rate limiting, traffic
  control, or Kong plugins.
- Do not implement Keycloak SSO yet.
- Do not install Prometheus, Grafana, Loki, Alertmanager, or observability
  dashboards yet.
- Do not create real TLS private keys manually.
- Do not create real SOPS age private keys.
- Do not commit real secrets.
- Do not commit kubeconfigs.
- Do not use manually applied cluster state as the source of truth.
- Do not require a Kubernetes cluster for local validation commands.
- Do not mutate any cluster unless the user explicitly runs the cluster
  apply/sync commands outside local validation.
- Do not implement later goals.

## Corrections to Carry Into Goal 001

Before or while implementing goal 001, inspect the goal 000 foundation and apply
small corrective fixes if needed.

Required carry-forward corrections:

- Preserve and verify the goal 000 secret-hygiene work.
- Confirm that any previous Booklore and Immich default/plain DB secret values
  remain replaced with explicit non-secret placeholders such as
  `CHANGE_ME_WITH_NON_REPO_SECRET`.
- These placeholders must remain visibly non-deployable.
- Strengthen secret validation if goal 001 introduces new manifest paths.
- Update `scripts/validate_repo.py` so it scans all new goal 001 directories
  for obvious unsafe material, including:
  - Plaintext passwords.
  - Default passwords.
  - Private keys.
  - Kubeconfig-like content.
  - Bearer tokens.
  - API tokens.
  - Deployable placeholder secrets.
  - `stringData` values that look like real credentials.
  - Base64 values that decode to obvious passwords or tokens, where practical.
- Keep legitimate examples and Kubespray submodule examples excluded only when
  there is a clear reason.
- Add or verify `.gitignore` coverage for local secret and cluster files.
- Ensure local-only sensitive files are ignored, including at minimum:
  - `.env`
  - `.env.*`
  - `*.key`
  - `*.pem`
  - `*.crt`
  - `*.p12`
  - `*.pfx`
  - `kubeconfig`
  - `kubeconfig.*`
  - `*.kubeconfig`
  - `.kube/`
  - `age.key`
  - `age.txt`
  - `.sops-age-key.txt`
- Do not ignore committed templates, documentation, or safe placeholder
  manifests.
- Keep `reports/goal-000-summary.md` as the goal 000 historical record.
- Add a new goal 001 evidence report at `reports/goal-001-summary.md`.
- Do not overwrite goal 000 evidence.
- Confirm the active source-of-truth hierarchy:
  - `README.md`
  - `ROADMAP.md`
  - `docs/architecture/*`
  - `docs/adr/*`
  - `platform/*`
  - `policies/*`
  - `tests/*`
  - `reports/*`
- Archived planning docs may remain, but must not contradict current active
  docs.
- Confirm `make validate` remains local-only.
- Do not make `make validate` require a Kubernetes cluster, internet access,
  SOPS private key, age private key, Argo CD access, or Helm repo network
  access.
- Split local validation from cluster validation.
- Add cluster-aware targets separately. Local validation must remain safe on
  any workstation.
- Confirm CI remains cluster-free.
- GitHub Actions or other CI created in goal 000 must continue to run without a
  Kubernetes cluster.
- Ensure all new Kubernetes YAML is validated statically.
- Add tests or scripts so namespace, Argo CD, MetalLB, cert-manager, SOPS, and
  NetworkPolicy structures are checked before cluster apply.
- Do not let placeholder secret material become deployable.
- Any placeholder secret documentation or template must clearly state that real
  secret values are generated or injected outside Git and must not be committed.

## Constraints

- This is an OSS Kong bank-lab platform project.
- The platform must remain compatible with Kong OSS and must not assume Kong
  Enterprise features.
- This goal must prepare platform prerequisites only.
- All new work must support a realistic but small regulated-bank simulation on
  a 3-node home Kubespray Kubernetes cluster.
- The platform prerequisite layer must be GitOps-first.
- All manifests must be declarative.
- All local validation must be runnable without a cluster.
- Cluster validation may require a working Kubernetes context, but it must be in
  separate targets.
- All cluster-affecting commands must be opt-in and clearly named.
- Do not make default make targets apply resources to the cluster.
- Do not use plaintext Kubernetes Secrets for real values.
- Do not commit private keys, cert private keys, kubeconfigs, passwords,
  tokens, API keys, or generated credentials.
- Do not generate or commit a real SOPS age private key.
- Do not include actual user-specific cluster IPs unless they are explicitly
  documented as examples.
- Do not assume a specific MetalLB address pool unless a clearly marked example
  range is used and documented as requiring local adjustment.
- Do not assume a public DNS provider.
- Do not require internet access for local validation.
- Do not require Helm chart downloads during local validation.
- Do not deploy anything automatically from CI.
- Prefer simple Kubernetes YAML, Kustomize, and GitOps structure over complex
  tooling.
- Use Kubernetes namespaces and labels to model bank-like ownership boundaries.
- Use NetworkPolicy defaults that are safe by design.
- NetworkPolicy must be prepared in a way that can be applied once the cluster
  CNI supports NetworkPolicy enforcement.
- If the current CNI does not enforce NetworkPolicy, documentation must say so
  and explain how to validate enforcement later.
- Argo CD app-of-apps must be defined structurally, but Argo CD itself does not
  need to be installed by this goal unless the repo already has a safe,
  intentional bootstrap pattern.
- If Argo CD installation manifests are included, they must be isolated under a
  bootstrap path and not automatically applied.
- MetalLB and cert-manager must be defined as prerequisite components, but this
  goal may provide installation values/manifests rather than applying them.
- SOPS/age must be structured and documented, but no real encrypted
  production-like secrets are required in this goal.
- Every new platform prerequisite must have at least static validation and
  documentation.

## Deliverables

### Repository Corrections From Goal 000

Apply the corrections listed in "Corrections to carry into goal-001" where
needed.

Update relevant tests and validation scripts so the corrections are enforced.

Do not rewrite goal 000 evidence except for legitimate spelling, formatting, or
historical clarification if absolutely necessary.

### Platform Prerequisite Directory Structure

Create or update the platform prerequisite structure.

Expected structure:

```text
platform/
|-- README.md
|-- namespaces/
|   |-- README.md
|   |-- kustomization.yaml
|   |-- platform-system.yaml
|   |-- platform-gitops.yaml
|   |-- platform-security.yaml
|   |-- platform-networking.yaml
|   |-- platform-observability.yaml
|   |-- platform-identity.yaml
|   |-- tenant-accounts.yaml
|   |-- tenant-payments.yaml
|   |-- tenant-cards.yaml
|   |-- tenant-customer-profile.yaml
|   |-- tenant-fraud.yaml
|   |-- tenant-open-banking.yaml
|   `-- synthetic-clients.yaml
|-- gitops/
|   |-- README.md
|   |-- app-of-apps/
|   |   |-- README.md
|   |   |-- root-app.yaml
|   |   |-- platform-prereqs-app.yaml
|   |   |-- namespaces-app.yaml
|   |   |-- networking-app.yaml
|   |   |-- security-app.yaml
|   |   |-- cert-manager-app.yaml
|   |   `-- metallb-app.yaml
|   `-- projects/
|       |-- README.md
|       |-- platform-project.yaml
|       |-- security-project.yaml
|       `-- tenant-project-template.yaml
|-- networking/
|   |-- README.md
|   |-- metallb/
|   |   |-- README.md
|   |   |-- kustomization.yaml
|   |   |-- namespace.yaml
|   |   |-- helm-values.yaml
|   |   |-- ip-address-pool.example.yaml
|   |   `-- l2-advertisement.example.yaml
|   `-- network-policies/
|       |-- README.md
|       |-- kustomization.yaml
|       |-- platform-default-deny.yaml
|       |-- tenants-default-deny.yaml
|       |-- allow-dns.yaml
|       |-- allow-gitops-to-managed-namespaces.yaml
|       |-- allow-observability-scrape-placeholder.yaml
|       `-- allow-ingress-controller-placeholder.yaml
|-- security/
|   |-- README.md
|   |-- sops/
|   |   |-- README.md
|   |   |-- .sops.yaml.example
|   |   `-- encrypted-secret.example.yaml
|   `-- policies/
|       |-- README.md
|       `-- namespace-labels.md
|-- certificates/
|   |-- README.md
|   `-- cert-manager/
|       |-- README.md
|       |-- kustomization.yaml
|       |-- namespace.yaml
|       |-- helm-values.yaml
|       |-- cluster-issuer-selfsigned.example.yaml
|       `-- cluster-issuer-banklab-ca.example.yaml
`-- bootstrap/
    |-- README.md
    |-- local-kind-not-used.md
    |-- apply-prereqs.example.sh
    `-- check-cluster-prereqs.sh
```

Small adjustments are allowed if the existing repo structure from goal 000
already uses equivalent paths, but the structure must remain clear and
documented.

### Namespace Baseline

Create namespace manifests for the platform and simulated tenants.

Required namespaces:

- `platform-system`
- `platform-gitops`
- `platform-security`
- `platform-networking`
- `platform-observability`
- `platform-identity`
- `tenant-accounts`
- `tenant-payments`
- `tenant-cards`
- `tenant-customer-profile`
- `tenant-fraud`
- `tenant-open-banking`
- `synthetic-clients`

Each namespace manifest must include labels for:

- `banklab.konghq.com/managed-by: gitops`
- `banklab.konghq.com/platform-layer: prereq`
- `banklab.konghq.com/environment: lab`
- `banklab.konghq.com/data-classification: synthetic`

Each namespace must also include an ownership label appropriate to the
namespace, for example:

- `banklab.konghq.com/owner: platform-team`
- `banklab.konghq.com/owner: tenant-accounts-team`

The exact label prefix may be adjusted if already established in goal 000, but
it must be consistent.

Create `platform/namespaces/README.md` explaining:

- Why namespaces model tenancy in the OSS lab.
- Which namespaces are platform-owned.
- Which namespaces are tenant-owned.
- What future resources may be deployed into each namespace.
- What must not be deployed in goal 001.

### Argo CD App-Of-Apps Structure

Create declarative Argo CD application structure, but do not require Argo CD to
be installed during local validation.

Required files:

- `platform/gitops/app-of-apps/root-app.yaml`
- `platform/gitops/app-of-apps/platform-prereqs-app.yaml`
- `platform/gitops/app-of-apps/namespaces-app.yaml`
- `platform/gitops/app-of-apps/networking-app.yaml`
- `platform/gitops/app-of-apps/security-app.yaml`
- `platform/gitops/app-of-apps/cert-manager-app.yaml`
- `platform/gitops/app-of-apps/metallb-app.yaml`

The Argo CD application manifests must be clearly marked as templates or lab
manifests that require repo URL adjustment if the actual remote repo URL is
unknown.

Do not use a fake repo URL that looks production-ready.

Use an obvious placeholder such as `REPLACE_WITH_REPO_URL`.

Validation must ensure this placeholder is present or documented when no real
repo URL is available.

Create Argo CD project examples:

- `platform/gitops/projects/platform-project.yaml`
- `platform/gitops/projects/security-project.yaml`
- `platform/gitops/projects/tenant-project-template.yaml`

The project examples must model restricted destinations and source repos where
possible.

The GitOps documentation must explain:

- App-of-apps intent.
- Sync boundaries.
- Drift detection intent.
- Rollback through Git revert.
- Why Git remains source of truth.
- Why Argo CD is not used to bypass PR review.
- How future goals will connect actual apps.

### MetalLB Structure

Create a MetalLB prerequisite structure.

Required files:

- `platform/networking/metallb/README.md`
- `platform/networking/metallb/kustomization.yaml`
- `platform/networking/metallb/namespace.yaml`
- `platform/networking/metallb/helm-values.yaml`
- `platform/networking/metallb/ip-address-pool.example.yaml`
- `platform/networking/metallb/l2-advertisement.example.yaml`

Do not assume the user's real LAN address pool.

The IP address pool example must use a clearly non-final placeholder or
documentation such as `REPLACE_WITH_LAB_LAN_LOADBALANCER_RANGE`.

If YAML schema requires concrete values, use a clearly documented RFC1918
example range and mark it as example-only.

The MetalLB README must explain:

- Why MetalLB is used in the home lab.
- How it maps to cloud LoadBalancer behavior.
- How the user should choose a safe LAN IP range.
- What validation can be done before applying.
- How to roll back.
- That no Kong service is created in this goal.

### cert-manager Structure

Create a cert-manager prerequisite structure.

Required files:

- `platform/certificates/cert-manager/README.md`
- `platform/certificates/cert-manager/kustomization.yaml`
- `platform/certificates/cert-manager/namespace.yaml`
- `platform/certificates/cert-manager/helm-values.yaml`
- `platform/certificates/cert-manager/cluster-issuer-selfsigned.example.yaml`
- `platform/certificates/cert-manager/cluster-issuer-banklab-ca.example.yaml`

Do not commit a real CA private key.

Do not create real production certificates.

Example issuers must be clearly marked as examples.

The cert-manager README must explain:

- Why cert-manager is used.
- How it will support later Kong TLS work.
- Why this goal does not issue Kong certificates.
- How short-lived lab certificates may be used later for rotation testing.
- Rollback considerations.
- Validation steps.

### SOPS/age Structure

Create a SOPS/age prerequisite structure.

Required files:

- `platform/security/sops/README.md`
- `platform/security/sops/.sops.yaml.example`
- `platform/security/sops/encrypted-secret.example.yaml`

Do not create or commit a real age private key.

Do not commit a real encrypted secret that requires a private key to validate.

The SOPS README must explain:

- Why Git must not contain plaintext secrets.
- How age keys should be generated outside the repo.
- Where the private age key must be stored.
- How public recipients are safe to commit when real recipients are chosen.
- How encrypted secrets will be introduced later.
- How key backup and recovery should work.
- How secret rotation will be tested in a later goal.

The example encrypted secret may be a non-functional documentation example if
necessary, but it must be clearly marked as an example and must not contain real
sensitive material.

If `.sops.yaml.example` contains an age recipient, use an obvious placeholder:
`REPLACE_WITH_AGE_PUBLIC_RECIPIENT`.

Validation must not require a real SOPS key.

### NetworkPolicy Baseline

Create baseline NetworkPolicy manifests.

Required files:

- `platform/networking/network-policies/README.md`
- `platform/networking/network-policies/kustomization.yaml`
- `platform/networking/network-policies/platform-default-deny.yaml`
- `platform/networking/network-policies/tenants-default-deny.yaml`
- `platform/networking/network-policies/allow-dns.yaml`
- `platform/networking/network-policies/allow-gitops-to-managed-namespaces.yaml`
- `platform/networking/network-policies/allow-observability-scrape-placeholder.yaml`
- `platform/networking/network-policies/allow-ingress-controller-placeholder.yaml`

The baseline must include default-deny examples for platform and tenant
namespaces.

The baseline must include a DNS egress allowance pattern.

The baseline must include placeholders for future observability scrape access
and future ingress-controller access.

Do not create a Kong-specific allow rule yet.

The NetworkPolicy README must explain:

- Default-deny intent.
- Expected CNI requirement for NetworkPolicy enforcement.
- How to test whether NetworkPolicy is enforced.
- How platform namespaces differ from tenant namespaces.
- What traffic is intentionally allowed in this goal.
- What traffic will be allowed later.
- Rollback procedure if a policy blocks required cluster traffic.

### Bootstrap Scripts

Create or update bootstrap scripts for cluster-aware validation only.

Required files:

- `platform/bootstrap/apply-prereqs.example.sh`
- `platform/bootstrap/check-cluster-prereqs.sh`

`apply-prereqs.example.sh` must be safe by default.

It must not run automatically from `make validate`.

It must include a clear warning that applying resources changes the cluster.

It may show example commands using:

```bash
kubectl apply -k platform/namespaces
kubectl apply -k platform/networking/network-policies
```

It must not apply Kong resources.

`check-cluster-prereqs.sh` must check for a current Kubernetes context and
report:

- Current context.
- Cluster reachability.
- Kubernetes server version.
- Whether required namespaces exist.
- Whether NetworkPolicy resources are accepted by the API server.
- Whether cert-manager namespace exists if applied.
- Whether MetalLB namespace exists if applied.

It must not require Kong.

It must not fail solely because Kong is absent.

### Makefile Targets

Update the `Makefile` while preserving goal 000 targets.

Keep these targets:

- `help`
- `validate`
- `test`
- `policy-test`
- `docs`
- `evidence`
- `clean`

Add these local-safe or cluster-explicit targets:

- `validate-yaml`
- `validate-kustomize`
- `validate-prereqs`
- `cluster-smoke`
- `cluster-prereq-smoke`
- `render-prereqs`
- `evidence-goal-001`

Target expectations:

- `make validate` must remain local-only.
- `make validate-yaml` must statically parse or validate YAML files where
  possible.
- `make validate-kustomize` must validate that kustomization files can render,
  if `kubectl kustomize` or `kustomize` is available. If the tool is
  unavailable, the command must fail with a clear message or provide a
  documented local fallback.
- `make validate-prereqs` must run all local prerequisite checks for goal 001.
- `make render-prereqs` must render Kustomize output for prerequisite paths
  where possible without applying it.
- `make cluster-smoke` must be cluster-aware and explicitly require a kube
  context.
- `make cluster-prereq-smoke` must check prerequisite resources if they were
  applied.
- `make evidence-goal-001` must generate or update
  `reports/goal-001-summary.md`.
- Do not make `make test` require a cluster.
- Do not make CI require cluster targets.

### Validation Scripts

Update `scripts/validate_repo.py` or add a new script if cleaner.

Validation must check:

- Goal 001 required directories exist.
- Goal 001 required files exist.
- Namespace manifests exist.
- Namespace manifests have required labels.
- No Kong resources exist in goal 001 manifests.
- No real secrets are committed.
- No kubeconfigs are committed.
- No private keys are committed.
- Argo CD placeholder repo URL is obvious if a real URL is not configured.
- MetalLB address pool is clearly example-only or replaced by a documented lab
  value.
- SOPS age private key is absent.
- `.sops.yaml.example` does not contain a private key.
- NetworkPolicy manifests exist.
- Evidence report path exists or can be generated.

Add or update `scripts/generate_evidence_report.py` so it can generate
goal-specific reports.

It may support:

```bash
python scripts/generate_evidence_report.py --goal goal-001-platform-prereqs
```

or a simple equivalent.

Do not break goal 000 evidence generation.

### Tests

Add tests for goal 001.

Create or update test files such as:

- `tests/unit/test_goal_001_prereqs_structure.py`
- `tests/unit/test_goal_001_namespace_metadata.py`
- `tests/unit/test_goal_001_no_kong_resources.py`
- `tests/policy/test_goal_001_prereq_policies.py`

Tests must verify:

- Required goal 001 files exist.
- Required namespaces are declared.
- Namespace labels are present.
- Argo CD app-of-apps files exist.
- MetalLB example files exist.
- cert-manager example files exist.
- SOPS example files exist.
- NetworkPolicy files exist.
- No Kong resources are introduced.
- No committed secret/private-key/kubeconfig patterns are introduced.
- Placeholder values are visibly non-production.

Tests must not require Kubernetes, Docker, or internet access.

Tests must run with pytest.

### Policy Checks

Update the policy placeholder structure so goal 001 has meaningful checks.

Policy checks should cover at least:

- Namespaces must have owner labels.
- Namespaces must have platform-layer labels.
- Namespace data classification must be synthetic.
- Forbidden Kong resource kinds must not appear in goal 001.
- Plaintext Secret manifests are forbidden unless explicitly marked as
  non-deployable examples.
- NetworkPolicy baseline must exist for platform and tenant namespaces.

Use the existing policy framework from goal 000 where practical.

If Rego/conftest is not fully available locally, keep pytest-based policy tests
that enforce equivalent rules.

### Documentation

Update documentation for goal 001.

Create or update:

- `docs/architecture/platform-prerequisites.md`
- `docs/architecture/gitops-bootstrap.md`
- `docs/architecture/network-policy-baseline.md`
- `docs/architecture/secrets-management.md`
- `docs/architecture/certificate-management.md`
- `docs/architecture/home-lab-networking.md`
- `docs/runbooks/platform-prereqs-rollback.md`
- `docs/runbooks/network-policy-recovery.md`

Documentation must explain:

- Prerequisite layer purpose.
- Namespace model.
- Platform versus tenant ownership.
- GitOps app-of-apps intent.
- Argo CD project boundary intent.
- MetalLB role.
- cert-manager role.
- SOPS/age role.
- NetworkPolicy baseline.
- Local validation.
- Cluster validation.
- Rollback approach.
- Known limitations.
- What is deliberately deferred until later goals.

Update `README.md` and `ROADMAP.md` if needed so goal 001 is reflected
accurately.

Do not convert the roadmap into implementation instructions for later goals.

### CI

Update `.github/workflows/ci.yml`.

CI must continue to run cluster-free checks only.

It must run at least:

```bash
make validate
make validate-prereqs
make test
make policy-test
make docs
```

Do not add `cluster-smoke` or `cluster-prereq-smoke` to CI unless they are
explicitly optional and skipped by default.

### Evidence Report

Create:

```text
reports/goal-001-summary.md
```

It must record:

- Goal name.
- Branch name if detectable or manually stated.
- Objective summary.
- Corrections carried forward from goal 000.
- Files and directories created or updated.
- Validation commands run.
- Validation results.
- Local-only checks performed.
- Cluster checks performed, if any.
- Cluster changes performed.
- Secrets created.
- Kong resources created.
- Enterprise Kong features used.
- Known limitations.
- Ready-for-next-goal statement.

The evidence report must explicitly state:

```text
Cluster changes performed: none
```

unless the user explicitly applied the prerequisite manifests manually during
the run and records that fact.

It must explicitly state:

```text
Kong resources created: none
```

It must explicitly state:

```text
Enterprise Kong features used: none
```

It must explicitly state:

```text
Secrets created: none
```

unless only non-secret examples/placeholders were created, in which case say:

```text
Secrets created: none; only non-deployable examples/placeholders were added
```

## Acceptance Criteria

- Goal 000 corrections have been inspected and applied where needed.
- Goal 000 validation remains passing.
- The repository contains a clear platform prerequisite structure.
- The required platform namespaces are declared.
- All namespace manifests include required ownership and classification labels.
- Argo CD app-of-apps manifests or templates exist.
- Argo CD project examples exist.
- MetalLB prerequisite structure exists.
- MetalLB address pool examples are clearly marked as examples or placeholders.
- cert-manager prerequisite structure exists.
- cert-manager issuer examples are clearly marked as examples.
- SOPS/age structure exists.
- No age private key is committed.
- No real encrypted production-like secret is committed.
- No plaintext real secret is committed.
- No kubeconfig is committed.
- NetworkPolicy baseline exists.
- Default-deny NetworkPolicy examples exist for platform and tenant namespaces.
- DNS allowance pattern exists.
- Future observability and ingress-controller NetworkPolicy placeholders exist.
- No Kong Gateway resources are created.
- No Kong-specific CRDs or manifests are introduced as active resources.
- No Kong plugins are introduced.
- No synthetic APIs are introduced.
- No Keycloak SSO implementation is introduced.
- No observability stack is introduced.
- Makefile has goal 001 validation targets.
- Local validation does not require a cluster.
- Cluster validation targets are explicit and opt-in.
- CI remains cluster-free.
- Documentation explains the prerequisite layer.
- Documentation explains how to apply and roll back prerequisites later.
- Documentation explains known limitations.
- Tests verify structure, labels, forbidden Kong resources, secret hygiene, and
  prerequisite files.
- Policy tests enforce the prerequisite baseline.
- The evidence report exists at `reports/goal-001-summary.md`.
- All required validation commands pass locally.

## Validation Commands

Run from the repository root.

Local validation gate:

```bash
make validate
```

Expected result: repository-wide validation passes and remains local-only.

```bash
make validate-yaml
```

Expected result: YAML files parse successfully and no unsafe YAML patterns are
found.

```bash
make validate-kustomize
```

Expected result: prerequisite Kustomize paths render successfully, or the
command reports a clear missing-tool message with documented install guidance.

```bash
make validate-prereqs
```

Expected result: all goal 001 local prerequisite checks pass.

```bash
make test
```

Expected result: all pytest tests pass.

```bash
make policy-test
```

Expected result: policy tests pass.

```bash
make docs
```

Expected result: documentation validates or builds successfully.

```bash
make evidence-goal-001
```

Expected result: `reports/goal-001-summary.md` is generated or refreshed.

Full local gate:

```bash
make validate && make validate-yaml && make validate-kustomize && make validate-prereqs && make test && make policy-test && make docs && make evidence-goal-001
```

Expected result: all local checks pass without Kubernetes access.

Optional cluster-aware checks, only if the user has a valid kube context and
intentionally wants cluster validation:

```bash
make cluster-smoke
```

Expected result: cluster connectivity and basic API reachability are reported.

```bash
make cluster-prereq-smoke
```

Expected result: prerequisite resources are checked if applied; Kong absence
must not be treated as a failure.

Do not run cluster apply commands unless explicitly requested by the user.

Do not include cluster apply commands in CI.

## Evidence Report

Create or update:

```text
reports/goal-001-summary.md
```

The report must contain this structure:

```text
Goal: goal-001-platform-prereqs
Status:
Branch:
Generated at:
Objective summary:

Goal 000 corrections reviewed:
-
Corrections applied:
-

Validation commands run:
- make validate:
- make validate-yaml:
- make validate-kustomize:
- make validate-prereqs:
- make test:
- make policy-test:
- make docs:
- make evidence-goal-001:

Optional cluster commands run:
- make cluster-smoke:
- make cluster-prereq-smoke:

Created files:
-

Updated files:
-

Namespace baseline:
-

GitOps app-of-apps structure:
-

MetalLB structure:
-

cert-manager structure:
-

SOPS/age structure:
-

NetworkPolicy baseline:
-

Local validation result:

Cluster changes performed:

Secrets created:

Kong resources created:

Enterprise Kong features used:

Known limitations:

Ready for next goal:
```

Required final report values unless the run explicitly proves otherwise:

```text
Cluster changes performed: none
Secrets created: none; only non-deployable examples/placeholders were added
Kong resources created: none
Enterprise Kong features used: none
Ready for next goal: goal-002-kong-oss-baseline
```

If any command could not be run, the evidence report must say:

- Which command was not run.
- Why it was not run.
- Whether this blocks completion.
- What the user must run locally.

Do not claim a validation command passed unless it actually passed.

## Stop Condition

Stop after goal 001 platform prerequisites are implemented or defined, goal 000
carry-forward corrections are handled, local validation passes, and
`reports/goal-001-summary.md` is created or updated.

Do not install Kong.

Do not add Kong manifests.

Do not create Kong Gateway API resources.

Do not add synthetic bank APIs.

Do not add API authentication, authorization, rate limiting, SSO, observability
stack, or day-2 incident workflows beyond prerequisite documentation.

Do not proceed to goal 002.

Stop with a summary in the evidence report only.

