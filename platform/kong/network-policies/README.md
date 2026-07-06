# Kong NetworkPolicy Baseline

These policies are conservative starting points for the Kong baseline. They
assume the cluster CNI enforces Kubernetes NetworkPolicy. If it does not,
`make kong-cluster-smoke` must record that enforcement is unverified.

Policy intent:

- Default deny ingress and egress for Kong pods.
- Permit DNS egress.
- Permit proxy ingress to Kong Gateway ports.
- Permit Kong Gateway to reach the platform smoke backend.
- Stage API server egress as an environment-specific rule.

The API server egress policy includes a private CIDR placeholder. Check the
actual Kubernetes service IP before applying in a real cluster.
