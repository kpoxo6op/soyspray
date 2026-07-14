---
name: argocd-kubernetes-application
description: Design or review a complete Argo CD and Kubernetes application. Use for Application and AppProject manifests, Kustomize packages, workload hardening, ownership, dependency ordering, network boundaries, observability, lifecycle controls, and GitOps end-to-end verification.
---

# Argo CD Kubernetes Application

Review the application as one operable system, not as a pile of valid YAML.

## Workflow

1. Map source repositories, Argo Applications, destinations, namespaces, cluster-scoped resources, request paths, secrets, telemetry, and user entry points.
2. Render every Kustomize or Helm source. Supply the target cluster's Kubernetes version and API capabilities when chart templates use `lookup` or `.Capabilities`, then compare against Argo's desired-resource inventory. Find files that are not referenced by a render, test, operator command, or documentation path; remove dead artifacts or make their purpose executable.
3. Check ownership. One reconciler should own each object. Avoid overlapping Applications and unexplained `ignoreDifferences` rules.
4. Check the AppProject against actual sources, destinations, and resource kinds. Prefer explicit permissions, while allowing chart-required cluster resources deliberately.
5. Check workload basics: pinned versions, probes that measure real health, requests and limits, disabled service-account token mounts, non-root execution, seccomp, dropped capabilities, and read-only filesystems where supported.
6. Check network paths in both directions. A default deny is only useful when DNS, ingress, gateway-to-upstream, controller-to-admin, and metrics flows have narrow allows.
7. Check lifecycle behavior. Starting, upgrading, rolling back, and stopping must be observable, retry-safe, and documented. Durable CRDs may remain when runtime workloads are parked if that tradeoff is explicit.
8. Check operations. Status should distinguish OFF, ON, and partial states. Smoke tests should prove success paths and important boundaries such as authentication, rate limiting, private admin surfaces, and UI availability.
9. Add tests before behavior changes, render locally, validate schemas, and perform a live GitOps reconciliation only after the branch is clean and pushed.

## Evidence standard

Collect proof from independent layers: source tests, rendered manifests, Argo sync and health, Kubernetes readiness, gateway responses, browser behavior, and final shutdown state. Do not infer runtime success from manifest validation alone.

Use current official Ansible, Argo CD, Kubernetes, and platform documentation for version-sensitive details.
