# Kong Cluster Apply Failure

Use this runbook when the cluster-apply gate cannot proceed or a runtime check
fails.

## Wrong Kubernetes Context

- Symptom: mutation guard reports a context mismatch.
- Likely cause: `BANKLAB_TARGET_CONTEXT` does not match `kubectl config current-context`.
- Diagnostics: `kubectl config current-context`.
- Safe mitigation: stop and correct the expected context only after operator confirmation.
- Rollback decision: none, if no mutation ran.
- Evidence: record expected and actual context.

## Missing Kubernetes Access

- Symptom: `kubectl` is unavailable or API calls fail.
- Likely cause: missing kubeconfig, network issue, or cluster outage.
- Diagnostics: `kubectl version`, `kubectl get --raw=/readyz`.
- Safe mitigation: restore access before mutation.
- Rollback decision: none, if no mutation ran.
- Evidence: command output and timestamp.

## Missing Gateway API CRDs

- Symptom: dry-run or apply rejects Gateway API kinds.
- Likely cause: Gateway API CRDs are not installed.
- Diagnostics: `kubectl get crd gatewayclasses.gateway.networking.k8s.io gateways.gateway.networking.k8s.io httproutes.gateway.networking.k8s.io`.
- Safe mitigation: stop unless CRD installation is explicitly approved.
- Rollback decision: none, if no Kong resources were applied.
- Evidence: missing CRD output.

## Missing MetalLB

- Symptom: proxy service remains pending or no external IP appears.
- Likely cause: no LoadBalancer implementation or address pool.
- Diagnostics: `kubectl get ns metallb-system`, `kubectl -n platform-kong get svc`.
- Safe mitigation: use documented port-forward fallback for route smoke; keep runtime approval pending unless external exposure is accepted.
- Rollback decision: rollback only if the operator wants the partial apply removed.
- Evidence: service status and fallback route result.

## Missing cert-manager

- Symptom: TLS examples cannot be validated.
- Likely cause: cert-manager is absent.
- Diagnostics: `kubectl get ns cert-manager`.
- Safe mitigation: keep TLS outside this gate unless separately approved.
- Rollback decision: none for non-TLS baseline.
- Evidence: namespace/status output.

## Failed Render Or Dry-Run

- Symptom: `make render-kong-baseline` or `make kong-install-dry-run` fails.
- Likely cause: invalid manifest, missing CRD, schema issue, or API rejection.
- Diagnostics: rerun the failing command and inspect the last error.
- Safe mitigation: fix code locally and rerun local validation.
- Rollback decision: none if apply did not run.
- Evidence: command output.

## Kong Or KIC Readiness Failure

- Symptom: Kong or KIC pods are not ready.
- Likely cause: image pull, config, RBAC, CRD, NetworkPolicy, or resource issue.
- Diagnostics: `kubectl -n platform-kong get pods`, `kubectl -n platform-kong describe pod`, `kubectl -n platform-kong logs`.
- Safe mitigation: collect evidence and decide whether to fix or rollback.
- Rollback decision: rollback if the baseline blocks the platform or cannot be recovered quickly.
- Evidence: pod status, events, logs.

## Gateway API Acceptance Failure

- Symptom: GatewayClass, Gateway, or HTTPRoute is rejected or not accepted.
- Likely cause: controller mismatch, missing CRDs, invalid listener, or route attachment issue.
- Diagnostics: `kubectl get gatewayclass`, `kubectl -n platform-kong describe gateway`, `kubectl -n platform-kong-smoke describe httproute`.
- Safe mitigation: fix manifests locally and reapply only after approval.
- Rollback decision: rollback if partial resources are confusing or unsafe.
- Evidence: status conditions.

## Route Smoke Failure

- Symptom: route returns 404, 5xx, timeout, or wrong body.
- Likely cause: HTTPRoute not accepted, backend unavailable, service issue, DNS/LoadBalancer issue, or NetworkPolicy block.
- Diagnostics: route smoke command output, HTTPRoute conditions, backend endpoints, proxy service state.
- Safe mitigation: use internal checks and port-forward fallback to isolate the failure.
- Rollback decision: rollback if traffic behavior is unsafe.
- Evidence: curl output and route status.

## Unknown Route Does Not Fail As Expected

- Symptom: unknown route succeeds or returns an unexpected response.
- Likely cause: catch-all route, proxy misrouting, or test host mismatch.
- Diagnostics: route definitions and smoke hostnames.
- Safe mitigation: stop runtime approval and fix routing.
- Rollback decision: rollback if unexpected exposure is possible.
- Evidence: request and response.

## Admin API Externally Reachable

- Symptom: Admin API can be reached through proxy, NodePort, LoadBalancer, Gateway, HTTPRoute, or Ingress.
- Likely cause: unsafe service or route exposure.
- Diagnostics: `make kong-admin-exposure-test`, service list, Gateway and HTTPRoute list.
- Safe mitigation: stop and rollback unless immediate code fix is safer.
- Rollback decision: strongly consider guarded rollback.
- Evidence: reachability proof and resource list.

## NetworkPolicy Blocks Expected Traffic

- Symptom: backend or proxy cannot reach expected paths.
- Likely cause: CNI enforcement and too-restrictive policy.
- Diagnostics: pod status, endpoints, events, and policy manifests.
- Safe mitigation: record exact blocked path and fix policy locally.
- Rollback decision: rollback if the platform cannot be restored quickly.
- Evidence: failed request path and policy set.
