# Synthetic API Runtime Failure

For any failure, record the symptom, command output, current Kubernetes context,
affected resource names, and whether rollback was run.

Common failures:

- Wrong Kubernetes context: stop, set `BANKLAB_TARGET_CONTEXT` correctly, rerun
  only after the current context matches.
- Missing tenant namespace: confirm the matching `platform/namespaces`
  manifest exists, run the guarded synthetic API tenant namespace bootstrap, and
  rerun the synthetic API server dry-run only after the namespaces exist.
- HTTPRoute not accepted or Gateway parent not found: inspect
  `kubectl get httproute -A -o yaml`, Gateway status, namespace labels, and
  allowed routes; fix manifests in the repo.
- Backend Service not found or pods not ready: inspect Deployment, Service,
  ConfigMap, events, and pod logs; fix the synthetic API manifest in the repo.
- NetworkPolicy blocks Kong-to-upstream: inspect policy selectors and CNI
  behavior; fix the tenant NetworkPolicy declaratively.
- Mock backend returns the wrong marker: inspect the ConfigMap and mounted nginx
  config; fix the generated mock response config in the repo.
- Internal route returns 404 or 5xx: inspect HTTPRoute status, Service endpoints,
  and Kong controller logs; fix the repo manifest, not a manual patch.
- External open-banking route returns 404: inspect external Gateway status,
  route hostnames, and LoadBalancer address.
- Internal API is reachable through external Gateway: stop; record evidence and
  fix the exposure policy and HTTPRoute manifests.
- Unknown host or unknown route does not fail safely: record the status/body and
  inspect Kong route matching.
- Admin API is externally reachable: stop; collect evidence and fix Admin API
  service/exposure before continuing.
- Rollback fails: collect the delete output, current rendered manifests, and
  remaining resources; decide with the user whether to leave state for
  investigation or run targeted repo-safe cleanup.

Rollback decision: only run guarded rollback after explicit approval, unless the
same approval already included `make synthetic-api-rollback`.
