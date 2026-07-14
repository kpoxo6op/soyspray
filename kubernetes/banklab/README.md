# Bank lab Kubernetes resources

This folder contains supporting workloads, tenancy, governance, and security
resources for the Kong bank lab.

| Folder | Purpose |
| --- | --- |
| [`customer-web/`](customer-web/) | Browser demo and synthetic traffic |
| [`docs-site/`](docs-site/) | In-cluster operator documentation |
| [`tenancy/`](tenancy/) | Namespaces, service accounts, roles, and ownership labels |
| [`governance/`](governance/) | Admission policy for approved Kong plugins |
| [`security/`](security/) | Authentication, authorization, rate limits, and related controls |

Kong platform resources live in [`../../platform/kong/`](../../platform/kong/).
Synthetic API workloads live in
[`../../apis/synthetic-bank/`](../../apis/synthetic-bank/).
