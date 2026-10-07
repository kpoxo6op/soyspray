# Kubernetes 1.36 and Ubuntu 24.04 readiness

This is a runbook, researched on 2026-10-07. It authorizes no live operation.
Production remains Kubernetes 1.35.4, Ubuntu 22.04 and stock Kubespray v2.31.0.
Healthy workloads do not establish support for a future Kubernetes release.

Ask: **“Follow docs/upgrade-readiness.md to upgrade the prerequisites and then
Kubernetes to 1.36, preserving data and identities.”** For OS maintenance, ask:
**“Follow docs/upgrade-readiness.md to move the nodes to Ubuntu 24.04, one at a
time, with console access and the existing removal/readd gates.”** These are
separate maintenance requests; stop at a failed safety gate.

Complete the Kubernetes work before **2027-02-28**, Kubernetes 1.35's
[end of life](https://kubernetes.io/releases/). Complete the OS work before
**May 2027**, Ubuntu 22.04's end of standard security maintenance; Canonical
publishes a month, not a specific day. Ubuntu 24.04 has standard maintenance
through May 2029. [Ubuntu release cycle](https://ubuntu.com/about/release-cycle)

## The next Kubespray tag

The next minor is [v2.32.0](https://github.com/kubernetes-sigs/kubespray/releases/tag/v2.32.0),
released 2026-09-22, upstream commit
`9751ea6f63244e433a7a6263d9ecf381e57bb8e9`. Recheck later v2.32 patches before
execution; do not substitute `master` defaults or skip Kubespray minors.

Its [checksum inventory](https://github.com/kubernetes-sigs/kubespray/blob/v2.32.0/roles/kubespray_defaults/vars/main/checksums.yml)
supports Kubernetes 1.34–1.36: 1.34.0–1.34.11, 1.35.0–1.35.8 and
1.36.0–1.36.4. The default is **1.36.4**. Kubernetes 1.36.5 is available today
but is absent from this tag's checksums: choose a later official v2.32 patch
with its checksum, or use 1.36.4 after reviewing its security status. Never
invent a checksum or treat the current upstream README as this tag's matrix.

The tag's [README](https://github.com/kubernetes-sigs/kubespray/blob/v2.32.0/README.md)
supports Ubuntu **22.04, 24.04 and 26.04**. Its
[requirements](https://github.com/kubernetes-sigs/kubespray/blob/v2.32.0/requirements.txt)
use Ansible **12.3.0 / core 2.19**, cryptography **50.0.1**, bcrypt `<6`,
jmespath 1.1.0, netaddr 1.3.0 and passlib 1.7.4. Our current recovery pins
core 2.18.18 and cryptography 46.0.7 conflict with that next tag. The future
tag PR must reconcile those pins, rebuild the development venv with
`make setup`, and pass the repository gate. Preserve the independent pinned
recovery service runtime until a deliberate runtime delivery.

Release notes require reviewing Ansible 2.19's strict booleans and Jinja
templating changes, containerd 2.3/config version 4, and Calico RBAC changes.
Use typed YAML or JSON for operational booleans. Argo and cert-manager addons
stay disabled even though v2.32 changes cert-manager namespace handling.

### Actual sample diff and inventory changes

The v2.31.0 and v2.32.0 sample `group_vars` have identical active top-level
values, but their comments and structure expose important changes. Compared
with our inventory, all **146** active top-level keys are referenced by the
new source. Preserve our OIDC, SANs, network ranges, VIP, labels, local storage,
strict ARP and enabled addons; sample defaults are not our desired values.
[New sample](https://github.com/kubernetes-sigs/kubespray/tree/v2.32.0/inventory/sample/group_vars)

- **Migrate the nested local provisioner keys:** `host_dir`, `mount_dir`,
  `volume_mode`, `fs_type` become `hostDir`, `mountDir`, `volumeMode`, `fsType`.
  The new template removes the automatic snake-case conversion. Render both
  versions and require identical `storageClassMap`, paths and PV identities
  before any run. Preserve `/mnt/disks`; do not create or clean storage.
- The sample moves `k8s_cluster/kube_control_plane.yml` to
  `group_vars/kube_control_plane.yml`. We have no active file at the old path;
  future control-plane-only settings belong in the new group file.
- Our three service-IP expressions use `kube_service_addresses`; the sample
  uses `kube_service_subnets.split(',') | first`. Resolve both against our
  single-stack inventory and require identical addresses before adopting the
  sample expressions. Preserve node-local DNS external zones and upstream DNS.
- Sample comments add kube-vip metrics and custom-CNI namespace/chart-auth
  settings, remove `eviction_hard_control_plane`, and update optional offline
  containerd and OpenStack CSI examples. These are disabled or unused here.
  Do not enable them by copying the sample wholesale.

The [download defaults](https://github.com/kubernetes-sigs/kubespray/blob/v2.32.0/roles/kubespray_defaults/defaults/main/download.yml)
select containerd 2.3.5, etcd 3.6.14, Calico 3.31.7, CoreDNS 1.14.2 for 1.36,
DNS autoscaler 1.10.3 and metrics-server 0.9.0. MetalLB remains 0.13.9,
node-local DNS 1.25.0, kube-vip 1.0.3 and local provisioner 2.5.0.
Review these actual changes as part of the full upgrade, including the retained
DNS autoscaler ConfigMap that upstream does not reconcile.

## Component compatibility with Kubernetes 1.36

Versions below are deployed images or declared chart versions, verified from
native state and Git. A minimum requirement, chart constraint or client version
is not a tested upper bound. “No upper range” means an isolated integration
proof is required, not an invented support claim. Refresh official matrices
when executing, because support windows change.

| Component now | Official range or evidence | Decision before 1.36 |
| --- | --- | --- |
| Argo CD 2.14.5, including its Dex/Redis bundle | [2.14 tested 1.28–1.31](https://argo-cd.readthedocs.io/en/release-2.14/operator-manual/tested-kubernetes-versions/); [3.5 tested 1.33–1.36](https://argo-cd.readthedocs.io/en/stable/operator-manual/tested-kubernetes-versions/) | Upgrade through reviewed minor/major migrations to a maintained 3.5 patch. Preserve external ConfigMaps, Secrets, signing key, OIDC and session cutoff. |
| cert-manager 1.17.1 controller/webhook/cainjector | [1.17: 1.29–1.33, EOL 2025-10-07; 1.21: 1.33–1.36](https://cert-manager.io/docs/releases/) | Upgrade sequential minors to a maintained 1.21 patch. Keep CRDs, issuers, certificates and private keys. |
| Longhorn 1.10.0 and bundled CSI/instance managers/engines | [Install minimum 1.25](https://longhorn.io/docs/archives/1.10.0/deploy/install/); [1.10 tested 1.30–1.33](https://longhorn.io/docs/archives/1.10.0/best-practices/). The older best-practices minimum disagrees with install requirements. [1.13 tested 1.33–1.36](https://longhorn.io/docs/1.13.0/best-practices/) | Upgrade 1.10 → 1.11 → 1.12 → maintained 1.13 patch, with volume/engine checks at each step. [1.13 installation requires 1.34+](https://longhorn.io/docs/1.13.0/deploy/install/); current 1.35 qualifies. |
| CNPG 1.27.0 / chart 0.26.0 | [1.27 supported 1.31–1.33, EOL 2026-03-09; 1.30 supports 1.34–1.36 and PostgreSQL 14–18](https://cloudnative-pg.io/docs/1.30/supported_releases/) | Move to a maintained 1.30 patch or later release with a 1.35/1.36 overlap. 1.30's published EOL is approximately December 2026, so refresh if executing later. Keep existing PostgreSQL majors (Authentik 17, Immich 16) and database/PVC identities. |
| Barman Cloud plugin 0.15.0, controller and sidecar | [CNPG ≥1.26, recommended ≥1.27; no separate Kubernetes upper matrix](https://cloudnative-pg.io/plugin-barman-cloud/docs/intro/) | Review current 0.15.1 patch and CNPG release compatibility. Both databases already use the plugin. Require completed backup/WAL and isolated restore after any plugin/operator change. |
| kube-prometheus-stack 78.2.0 / CRDs chart 16.0.1 / Prometheus Operator 0.86.0 | [Chart requires ≥1.25](https://github.com/prometheus-community/helm-charts/blob/kube-prometheus-stack-78.2.0/charts/kube-prometheus-stack/Chart.yaml); [operator minimum 1.16, no upper matrix](https://github.com/prometheus-operator/prometheus-operator/blob/v0.86.0/README.md) | Update chart and separately owned CRDs together to a maintained release; stage on 1.36. Preserve native rule/dashboards ownership, metrics claim and Alertmanager identity. |
| kube-state-metrics 2.17.0 | [Client-go 1.33; 2.20 uses 1.36](https://github.com/kubernetes/kube-state-metrics#compatibility-matrix). A client version is not a server support range. | Choose a chart bundling 2.20 or a supported later compatible client. Verify all alert metric names and labels. |
| Prometheus 3.6.0, Alertmanager 0.28.1, Grafana 11.3.0, sidecar 1.30.10, node-exporter 1.9.1, smartctl-exporter 0.14.0 | Bundled stack dependencies; [chart metadata](https://github.com/prometheus-community/helm-charts/blob/kube-prometheus-stack-78.2.0/charts/kube-prometheus-stack/Chart.yaml) has the Kubernetes minimum, no individual 1.36 matrices | Verify stack scrape/query/rule/reload and delivery counters; avoid sending a test bot message during another consumer's session. |
| MetalLB 0.13.9 controller/speaker | [Installation requirements](https://metallb.io/installation/) have no per-release tested upper range; v2.32 bundles this same version | Keep Kubespray ownership/default resources. Stage L2 address allocation, failover and webhooks on 1.36; no independent patch or adoption. |
| Calico 3.31.5; v2.32 selects 3.31.7 | [3.31 tested 1.32–1.35](https://docs.tigera.io/calico/3.31/getting-started/kubernetes/requirements); [3.32 tested 1.34–1.36](https://docs.tigera.io/calico/3.32/getting-started/kubernetes/requirements) | Stock v2.32's selection lacks a published 1.36 test range. Prefer an official subsequent tag with tested Calico, moving one tag at a time. Otherwise require the isolated full Kubespray/Calico 1.36 proof described below; do not fork roles or override unprovided checksums. |
| ingress-nginx 1.13.3 | [Tested 1.29–1.33](https://github.com/kubernetes/ingress-nginx#supported-versions-table); [retired March 2026, no further fixes](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/) | Replace before 1.36. It is a retained legacy install, outside Argo and the pinned Kubespray role. Do not mistake it for the nginx image used inside application pods. |
| ExternalDNS 0.14.0 | [0.10–0.17 supports 1.19–1.32; ≥0.18 required for ≥1.33](https://github.com/kubernetes-sigs/external-dns#kubernetes-version-compatibility) | Upgrade to a maintained ≥0.18 release before 1.36. Preserve provider credentials, TXT owner ID, zones, sources and registry; verify no unintended record deletion. |
| Reflector 10.0.3 | [Kubernetes ≥1.22, no upper matrix](https://github.com/emberstack/kubernetes-reflector#prerequisites) | Stage Secret/certificate reflection, preserving source keys and namespace boundaries. Upgrade if its maintained release requires it. |
| metrics-server 0.8.1 | [0.8 supports ≥1.31](https://github.com/kubernetes-sigs/metrics-server/blob/v0.8.1/README.md#compatibility-matrix) | Take v2.32's 0.9.0 through Kubespray and verify `kubectl top`/metrics API with its release matrix. |
| CoreDNS 1.12.4 / node-local DNS 1.25.0 / DNS autoscaler 1.8.8 | [CoreDNS Kubernetes plugin](https://github.com/coredns/coredns/tree/v1.12.4/plugin/kubernetes), [node-local DNS](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/), [autoscaler](https://github.com/kubernetes-sigs/cluster-proportional-autoscaler): no per-image upper matrices | Use tag defaults above, preserve existing DNS ConfigMap data, and test service/external resolution from all nodes. |
| kube-vip 1.0.3 | [Static control-plane installation](https://kube-vip.io/docs/installation/static/): no per-release upper range | Stock tag integration; test VIP failover, CA/SAN validation and OIDC, retaining the address/interface. |
| local static provisioner 2.5.0 | [Official release source](https://github.com/kubernetes-sigs/sig-storage-local-static-provisioner/tree/v2.5.0): no 1.36 upper matrix | Apply nested-key migration above in the future tag PR; prove identical rendered map and existing PV bindings. |
| etcd 3.6.10 / containerd 2.2.3 / runc / kube-proxy/control plane 1.35.4 | [Kubespray tag defaults](https://github.com/kubernetes-sigs/kubespray/blob/v2.32.0/roles/kubespray_defaults/defaults/main/download.yml) are the integration contract for 1.34–1.36 | Use tag-selected versions in the full upgrade; preserve etcd membership, CA, host storage and runtime configuration. |
| Headlamp 0.35.0 | [Release/source](https://github.com/kubernetes-sigs/headlamp/releases/tag/v0.35.0): no published per-release Kubernetes upper matrix | Stage API discovery, RBAC and OIDC; update to a maintained release if discovery fails. |
| Authentik 2026.5.6 server/worker and proxy outpost | [Kubernetes installation](https://docs.goauthentik.io/install-config/install/kubernetes): no per-release upper matrix | Stage outpost reconciliation and auth redirects. Keep database, signing keys, users, sessions and provider credentials. Refresh security patch status separately; an auth change requires Boris's real login test. |

The remaining deployed images are applications or bundled helpers, not omitted
operators: Immich 2.3.1, PostgreSQL 16/17, Redis, Jellyfin, Home Assistant 2026.5.4,
Zigbee2MQTT 1.42.0, Mosquitto 2.0.18, Wyoming voice services, GI, Boys,
Autism Traits, Domain Health, media-helper/node-backup, Dispatcharr, Booklore,
LazyLibrarian, qBittorrent, MariaDB, CouchDB, Vaultwarden,
Loki 3.3.2, Alloy 1.11.2, Cloudflared, Restic, AWS CLI and
application nginx containers. Their [Git sources and app READMEs](https://github.com/kpoxo6op/soyspray/tree/main/apps)
identify the exact immutable versions and normal checks. They publish no common
Kubernetes support range; check any individual chart constraints when changing
them. Stage their existing stable Kubernetes APIs, storage
access and public/user checks on 1.36; keep application images unchanged during
the foundation upgrade. Kong CRDs are retained, but no Kong operator is running.
CSI sidecars belong to the Longhorn version, not a separate upgrade owner.

## Prerequisites, in order

Each step is a CI-green merged PR, followed by native and user-boundary
verification on current Kubernetes 1.35. Stop if any identity, backup or restore
gate fails. Do not retarget Applications to a branch or re-enable Kubespray
Argo/cert-manager addons.

1. Refresh native state and the matrix; establish completed backups, isolated
   database/storage restores and off-cluster unlock access. Retain etcd
   snapshots, protected CRDs/PVCs and private inputs. A schedule is insufficient.
2. Upgrade cert-manager one minor at a time through 1.21; validate webhook,
   issuance/renewal and unchanged issuers/keys. This precedes plugin changes.
3. Review/update Barman plugin, then CNPG through reviewed release transitions
   to a maintained 1.30+ version supporting both 1.35 and 1.36. Preserve PostgreSQL
   majors (Authentik 17 and Immich 16), ObjectStore destinations, archive server
   names, schedules and WAL.
   Prove isolated restores for both databases after the final transition.
4. Upgrade Longhorn one minor at a time through 1.13, including its supported
   [manager and engine sequence](https://longhorn.io/docs/1.13.0/deploy/upgrade/longhorn-manager/).
   Require healthy RW replicas, completed backups and isolated restore before
   each transition. Preserve the intentionally detached Jellyfin config volume.
5. Upgrade Argo through its [migration guides](https://argo-cd.readthedocs.io/en/stable/operator-manual/upgrading/overview/)
   to maintained 3.5, keeping the existing non-pruning ownership boundaries and
   privately managed configuration. Verify OIDC and admin recovery; never restore
   the public credential. Upgrade ExternalDNS and the monitoring chart/CRDs,
   including kube-state-metrics, and verify DNS/alert/dashboard contracts.
6. Replace ingress-nginx through a reviewed migration. A concrete candidate is
   **Envoy Gateway 1.9** (officially tested 1.33–1.36) with Gateway API 1.6.1;
   [its matrix](https://gateway.envoyproxy.io/news/releases/matrix/) currently
   gives EOL 2027-02-14, so refresh the candidate before a later execution.
   Install it under Argo with a separate temporary address, migrate every route
   and test TLS, Authentik forward auth, Argo redirect, websockets, large Immich
   uploads and Jellyfin playback. Preserve original addresses/hostnames and
   certificate Secrets at cutover. Retire the old controller only after its
   replacement serves all routes; a reviewed scoped operation owns retirement.
7. Resolve the Calico support gap. Prefer a stock upstream tag with a published
   1.36-tested Calico. If retaining stock v2.32, substitute **an isolated
   three-node VM cluster built by the exact unmodified tag**, upgraded 1.35→1.36,
   with Calico networking/policy, MetalLB L2/failover, DNS, local provisioner,
   Longhorn read/write and backup/restore, operator admission and application
   checks. Record versions and results; a kind smoke test or task listing cannot
   replace this proof. A failing result blocks production.
8. Prepare the v2.32 tag/toolchain/inventory PR, including the nested local
   provisioner migration. Resolve all host variables, render affected templates,
   prove zero eligible Kubespray Argo/cert-manager tasks and run `make check`.
   Merge with CI green. Use the official loop below for the live upgrade.

## Full Kubernetes upgrade

Use the [foundation guide](https://github.com/kpoxo6op/soyspray/tree/main/inventory/soycluster)
for exact health/snapshot commands. Move one Kubespray tag at a time, read release
notes and diff the sample, install that tag's requirements, select supported
`kube_version`, and verify an etcd snapshot's private copy. Then run:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i inventory/soycluster/hosts.yml \
  --become --become-user=root --user ubuntu kubespray/upgrade-cluster.yml
```

No extra-vars files, tags or host limits. Inventory alone carries OIDC. Before
the run require three Ready nodes, healthy etcd, every Application Synced and
Healthy, healthy attached Longhorn volumes and no warning/critical alerts.
Afterward verify all node versions, etcd membership, CA/SAN/VIP and OIDC,
networking/DNS, CRDs/admission, storage identities/replicas, backups/restores and
the affected real application journeys. Take a fresh native capture. Source
revert does not downgrade Kubernetes; a failed foundation upgrade requires its
reviewed recovery procedure, not an improvised reset or etcd restore.

## Ubuntu 22.04 → 24.04, one node at a time

Use the existing [native removal/readd procedure](https://github.com/kpoxo6op/soyspray/tree/main/playbooks/operations/nodes),
with an **in-place OS release upgrade between removal and readd**. Avoid a
reimage: node-0's root, storage, media mounts and devices must retain their
identities. [Ubuntu's supported LTS upgrade procedure](https://ubuntu.com/server/docs/how-to/software/upgrade-your-release/)
owns the release upgrade. Do not combine it with a Kubernetes version change.

1. Confirm the selected Kubespray tag supports 24.04, the current Kubernetes
   version and the target kernel. Capture filesystem UUIDs/mounts, boot/network
   configuration, Longhorn disk identity, SSH credentials and node-specific
   devices. Verify off-cluster recovery inputs and an OS recovery path before
   removal. Have a usable physical console or independently tested KVM, power
   access and recovery media for **each** node; SSH alone is not sufficient.
2. Start with **node-2**, then **node-1**, then **node-0**. Recheck inventory group
   order before each: move a first control-plane/etcd member last through merged
   Git and reconcile while it is present, exactly as the existing guide says.
   Require three healthy nodes/etcd and the existing storage gates each time.
3. Take/verify the etcd snapshot and survivor kubeconfig/discovery endpoint.
   Perform the existing normal drain/removal once, without lowering PDBs or
   storage protections. A drain blocker stops the operation; the disruptive
   fallback needs separate explicit scope, not past drill authorization.
4. With the target removed and survivor quorum healthy, follow Ubuntu's
   preparation and `do-release-upgrade` to 24.04, retaining disks and the Ubuntu
   user/SSH identity. Review config prompts at the console, retain intended
   network/SSH/storage settings, and reboot. Restore iSCSI/NFS prerequisites,
   required kernel modules and unchanged mounts before readd. Do not let apt
   replace Kubespray's Kubernetes/container runtime with distro packages.
5. Run full stock `cluster.yml` from the merged inventory to readd. Verify new
   Node UID, preserved machine/host/disk identities, three Ready/schedulable
   nodes, healthy etcd, Longhorn replicas and real application/data access.
   Finish all recovery before removing the next node.

Node-0 goes last because its local PVs, `/storage`, `/srv/media`, Zigbee and GPU
make physical recovery and downtime more consequential. Verify NVIDIA driver/
runtime support on the selected 24.04 kernel before its upgrade; afterward test
GPU playback, the same Zigbee coordinator without pairing, Home Assistant and
voice. The earlier drills did not prove a release upgrade or physical playback.
If boot/network/mount identity is wrong, stop at console recovery; do not
format disks, delete PVCs, flush active maps or continue to another node.

An OS source revert does not undo a release upgrade. The recovery plan must
include a verified OS backup or reviewed retained-disk recovery, not a blind
reinstall. Large media trees are outside the selected node-local backup scope.
