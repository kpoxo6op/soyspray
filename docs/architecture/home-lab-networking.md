# Home-Lab Networking

The home lab uses Kubernetes on a small cluster. MetalLB will provide
LoadBalancer semantics for later gateway work.

Goal 001 does not assume the real LAN range. The MetalLB address pool example
uses a clearly documented example range and a replacement annotation.

Before applying MetalLB in a later or explicit operation:

- Reserve a safe IP range outside DHCP.
- Confirm the router will not hand those addresses to clients.
- Confirm the CNI and L2 network support the desired behaviour.
- Document the final range in the deployment evidence.

