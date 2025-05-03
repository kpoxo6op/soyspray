# Longhorn troubleshooting session – summary (up to disk‑space root‑cause)

TLDR - Longhorn does not use SSDs as disks and ran out of space on emmcs storage.

## 1  Context

* Home lab Kubernetes cluster (`soycluster`) with 4 nodes
  * **node‑3** control‑plane & worker
  * **node‑0/1/2** workers
* Longhorn v1.8.0 provides the storage layer (one 500 GB SSD per node, mounted at `/storage`).

After an **Ansible‐driven reboot of _node‑1_** a media‑stack Pod (`qbittorrent`) stayed in `Init:0/1` because its PVC volume
`pvc‑9dcdc023‑…` could not attach:

```
AttachVolume.Attach failed … volume … is not ready for workloads
```

Longhorn UI showed the volume in state **Faulted**.

---

## 2  Initial investigation

### 2.1  Longhorn health script

* All system pods healthy.
* Volume `pvc‑9dcdc023‑…` in `detached / faulted`.
* Replica `…‑r‑ee3b0007` exists on **node‑1** but volume cannot be salvaged.

### 2.2  Disk problem on node‑1

`kubectl -n longhorn-system get lhn node-1 -oyaml` revealed:

* Disk condition **Ready = False**, **Schedulable = False**.
* Reason: **DiskFilesystemChanged** (UUID mismatch).

On the node:

```
/storage          → ext4 on /dev/sda (new UUID 4c75…)
.longhorn/uuid    missing
longhorn-disk.cfg still had old UUID 4594…
```

---

## 3  Fixing the UUID mismatch

Commands executed on **node‑1**

```bash
sudo mkdir -p /storage/.longhorn
echo 4c750695-e258-4807-b7dc-f4a2730f735d | sudo tee /storage/.longhorn/uuid
sudo sed -i -E 's/"diskUUID":"[^"]+"/"diskUUID":"4c750695-e258-4807-b7dc-f4a2730f735d"/'             /storage/longhorn-disk.cfg
```

Longhorn‑manager pod on node‑1 was deleted to reload disk metadata:

```bash
kubectl -n longhorn-system delete pod $(kubectl -n longhorn-system get pods -l app=longhorn-manager -o wide | awk '$7=="node-1"{print $1}')
```

Result:

```
Ready  = True
```

but

```
Schedulable = False
Reason: DiskPressure
```

---

## 4  Root cause – **disk pressure rule**

Node‑1 SSD is almost full.  Longhorn subtracts `storageReserved`
(currently **150 GB**) and then requires at least **25 % free space** of
`storageMaximum`.  Only ~18 GB were available, so the disk is marked **unschedulable**,
blocking the salvage.

> ➜ Either lower `storageReserved` or free space, then the salvage of
>   `pvc‑9dcdc023‑…` will succeed.

The actual salvage step and application restart were deferred to the next session.

---

### 5  Key commands to run next

```bash
# Option A – shrink reservation to 20 GiB
kubectl -n longhorn-system patch lhn node-1 --type=json -p='[
  {"op":"replace",
   "path":"/spec/disks/default-disk-bc33fded6a329dd/storageReserved",
   "value":21474836480}
]'

# After Schedulable=True
rep="pvc-9dcdc023-d2d3-4679-a6f1-b244a13e5d3a-r-ee3b0007"
kubectl -n longhorn-system patch lhv pvc-9dcdc023-d2d3-4679-a6f1-b244a13e5d3a   --type=json -p="[ {"op":"add","path":"/spec/salvageRequests",   "value":[{"replicaName":"$rep"}] } ]"

# Finally
kubectl -n media scale deploy qbittorrent --replicas=1
```

---

*Last updated 2025‑05‑03*
