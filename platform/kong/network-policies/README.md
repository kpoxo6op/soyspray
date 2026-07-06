# Kong NetworkPolicy Baseline

These policies are conservative starting points for the Kong baseline. They
assume the cluster CNI enforces Kubernetes NetworkPolicy. If it does not,
`make kong-cluster-smoke` must record that enforcement is unverified.

Policy intent:

- Default deny ingress and egress for Kong pods.
- Permit DNS egress.
- Permit KIC to reach the Kubernetes API service and control-plane endpoints.
- Permit KIC to reach Kong Gateway's private Admin API service.
- Permit proxy ingress to Kong Gateway ports.
- Permit Kong Gateway to reach the platform smoke backend.

The API server egress policy is verified for this home cluster:
`10.233.0.1:443` with control-plane endpoints
`192.168.20.10-12:6443`.
