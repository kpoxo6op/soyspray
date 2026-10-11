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
cleanup confinement, including rerun after a real process interruption during reset.
Scenario tests own observable effects of the controls.

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
the receiver Pod. It can get Pods and Jobs and get/create Pod exec in this namespace;
it cannot read secrets or mutate workloads. The reviewed operation verifies
the controller archive, PVC UID, retained PV, Job owner, pod labels, running
phase, fixed receiver command and image digest before its one fixed transfer.
No operator shell is invoked, and no token is printed or written to disk.
The WebSocket handshake uses HTTP GET; Kubernetes 1.35 also checks create
permission for this same exec subresource. Both verbs are scoped to this namespace
and checked with the issued credential before transfer.

Production intake is a Sync hook in a wave before the web Deployment. Restore
intake is a separate PostSync hook on the restore-test claim. Both use fixed
names, BeforeHookCreation only, a bounded deadline and no TTL. Completed and
failed Jobs remain for diagnosis until the next declared sync. An identical
completed pack is fully verified and the receiver exits without opening a
transfer socket. The operator records Job and Pod UIDs, node, digest, claim/PV,
completion log and the matching Argo hook result before any subsequent sync.

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

Both receiver hooks request 128Mi and limit memory to 1Gi, at least 100Mi above
the 900Mi archive bound. Longhorn NFS writeback pages count against that limit;
record node capacity before promotion. On kernels without `memory.peak`, a
read-only node watcher samples the exact Pod and container cgroups every 10ms
from before transfer until exit, with memory.stat at least every 100ms.
Record IDs, timing, sample gaps and the sampled maximum. Verification requires
oom, oom_kill and max counters to remain zero at both levels, a sampled maximum
at most 640Mi, and the completed full-hash proof. A breach requires reviewed
bounded writeback code, a new scanned image and another real NFS proof.
The receiver now fsyncs and discards its completed write cache every 8Mi; hashing
and archive extraction also discard clean read cache periodically. These Linux
hints change cache residency, not file contents or the durable publication order.
Live memory measurements remain mandatory because NFS behaviour is kernel-specific.

`retire-stale-sync.yml` documents the one-time recovery from the obsolete initial
192Mi operation when another Argo retry remains. Run only from clean, pushed main
with the merged 1Gi configuration and private reviewed Application/Job/Pod IDs.
It refuses a changed operation, existing web workload or active sender, checks
unchanged staging, and records hook/operation/events before requesting native
Argo termination. Its only write changes that obsolete operation's status phase;
Argo owns cleanup and the subsequent main sync. It never edits or deletes Jobs,
claims, deployments or Application spec. Do not reuse it as a general sync shortcut.
Its second reviewed incident is the memory-unverified operation at `0196736b`,
waiting at its original restore hook. It requires the new bounded-writeback image
and provenance-only pack on main, a completed earlier production hook, recorded
production state, and fresh native-API 401 evidence before the status-only route.
Both incidents have fixed original revisions and exact private identity guards.

The private backup repository contains only age ciphertext and allowlisted
metadata: schema version, manifest ID, archive/ciphertext/source-video SHA256,
ciphertext size, age version, public recipient, archive-derived asset name and UTC.
Audit every commit on every ref, tag message, release text and asset name; scan
history and release text for transcript/OCR phrases and private profile strings.
No talk-derived material, identity, identity hash, key location or hostname mapping
belongs in GitHub. Every asset must have an age header and one X25519 stanza,
with its bytes and size matching the server and immutable controller pins.
The stanza contains an ephemeral key; successful independent decryption binds
the encrypted asset to the enrolled recovery identity.

At backup and restore, timestamp the installed-App repository selections and
Contents permissions and compare the baseline. Newly granted backup-repository
or all-repository access blocks verification until reviewed; do not change grants
automatically. Existing Apps were reviewed and left unchanged. Apps can read
ciphertext and, with write permission, alter or delete it. Confidentiality rests
on age and separate key custody, integrity on controller-pinned hashes, and
availability on the immutable controller inputs. A missing or mismatched asset
requires re-upload and a complete independent restore.

Audit that the repository is private, owner-only, with zero invitations, deploy
keys, hooks and forks; Actions, Pages, Issues, Wiki, Projects and Discussions are
disabled. The account's allow-forking flag cannot be disabled; check actual forks.
The recovery identity stays outside Git, CI, the cluster, Telegram and logs.
Its desktop Secret Service keyring copy and off-device private pCloud copy are
verified independently. The pCloud account has two-factor authentication and
the dedicated folder has no shares, public/upload links or collaborators.
Server listing and a fresh server download prove custody. Key-location evidence
stays on the private controller.
Delivery requires a completed encrypted upload, independent download,
decryption from both recovery copies, full hash comparison and identical intake
into the protected restore-test claim.

Rollback promotes the previous tested image and manifest ID together. Keep the
old pack and its encrypted backup. No existing application data is moved.
