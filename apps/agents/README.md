# Agent workshop

Private learning site for studying coding-agent verification, skills, coordination
and safe delivery. The static application includes evidence-linked lessons,
deterministic scenarios, an offline lab and browser-local progress and exports.
It has no model API, application backend, analytics or cluster controls.

Public source contains original teaching text and references. Recording bytes,
transcription, screenshots, OCR, narration and corrections belong exclusively to
a private evidence pack, never this repository or the runtime image. Audience
assessment and source account evidence remain private controller inputs.

## Normal use

The intended private host is `https://agents.soyspray.vip`, through the same
Tailscale split DNS and nginx ingress pattern as the assembly helper. The Talk
area synchronizes replay, captions, transcript and keyframes. Lessons have
additive Basics and Deep layers. The simulator is illustrative, with scripted
outcomes rather than measured error rates. The lab executes only owned local
scratch files with Python's standard library and Git; a real-model rerun is a
separate optional activity in an uncredentialed VM or container.

## Checks

Run `make check APP=agents` with the repository Python environment. Image CI runs
the offline lab in a clean build container with networking disabled, checks the
real nginx entrypoint and publishes only the tested immutable image. Browser QA
must cover replay, deep timestamps, caption MIME type, reduced motion, keyboard
navigation, reflow, axe and a truthful screen-reader report. Automated scans do
not constitute WCAG conformance.

Receiver tests own the data boundary: an archive attack or incomplete intake
must never publish a completed pack. Lab tests own refusal before writes and
cleanup confinement. Scenario tests own observable effects of the controls.

## Ownership and release

Argo owns every Kubernetes object from `main`. Ansible owns the bounded private
data intake. A source PR publishes an image without activating it. A separate
provisioning promotion catalogs the StorageClass and protected namespace, two
4Gi RWX claims and narrowly scoped intake identity. It does not create a Job,
web Deployment or ingress. Read the assigned PVC UIDs and retained PV identities
before a runtime promotion pins the image, manifest ID, archive SHA and UIDs.

`storage/` contains exactly one cluster-scoped resource: the dedicated retained,
non-default StorageClass. It copies the existing RWX class parameters without
changing that class or any existing volume. `provision/` owns the new namespace,
claims, scoped RBAC and default-deny NetworkPolicy. Root catalog entries and
durable resources are protected from pruning and cascading deletion.

The intake credential exists in memory for at most 30 minutes and is bound to
the receiver Pod. It can get Pods and Jobs and create Pod exec in this namespace;
it cannot read secrets or mutate workloads. The reviewed operation verifies
the controller archive, PVC UID, retained PV, Job owner, pod labels, running
phase, fixed receiver command and image digest before its one fixed transfer.
No operator shell is invoked, and no token is printed or written to disk.

Run the pushed operation with the repository environment:

```sh
ansible-playbook playbooks/operations/agents/intake.yml \
  -e agents_promotion=/private/reviewed-promotion.json \
  -e agents_archive=/private/evidence.tar \
  -e agents_report=/private/intake-report.json
```

## Pack and recovery

`pack.py SOURCE ARCHIVE` creates canonical UTF-8 JSON (sorted keys, compact
separators, trailing LF) listing all content files in bytewise path order.
The manifest ID is SHA256 of those manifest bytes, excluding the manifest itself
and COMPLETE. Archive SHA256 is a separate identity. USTAR entries are sorted,
regular files only, mtime/uid/gid zero, empty user/group names and mode 0644.
Every file hash, file count and byte total is validated on both sides of intake.

Receiver output is `versions/MANIFEST_ID/`, never a mutable current link. Files
are 0444 and directories 0555. Moving a directory across parents requires its
root to stay writable through the rename; read-only startup verification also
checks the final root mode before readiness. A matching owned partial intake
can recover; an unknown partial aborts. Identical complete versions are no-ops.
Previous versions are retained. Retirement requires a separate reviewed
operation. Alarm at 75% claim capacity; no generic backup expiry is introduced.

The web claim is read-only; startup verifies COMPLETE, the promoted manifest ID
and all file hashes. Failed verification leaves the new pod unready while the
old pod serves. Web and receiver Pods keep zero egress; kubelet's Longhorn NFS
mount path must be proven live without loosening their policy. The restore-test
claim is distinct and must never be mounted by the web Deployment.

Private text history goes to a private evidence repository with Actions, Pages,
forks, collaborators, deploy keys and hooks disabled or absent. Media release
assets are age-encrypted, with ciphertext hash/size recorded privately. The
identity stays outside every Git repo with a verified password-manager or
offline copy. Delivery requires a completed upload, independent download,
decryption from that second copy, full hash comparison and identical intake
into the protected restore-test claim.

Rollback promotes the previous tested image and manifest ID together. Keep the
old pack and its encrypted backup. No existing application data is moved.
