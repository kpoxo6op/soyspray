import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def documents(directory):
    return [
        d
        for file in (ROOT / directory).glob("*.yaml")
        for d in yaml.safe_load_all(file.read_text())
        if d and d["kind"] != "Kustomization"
    ]


class StorageScope(unittest.TestCase):
    def test_storage_source_cannot_gain_other_cluster_objects_or_become_default(self):
        # AppProject whitelist is kind-scoped. This independent source boundary prevents wider ownership.
        docs = documents("storage")
        self.assertEqual(len(docs), 1)
        storage = docs[0]
        self.assertEqual(storage["kind"], "StorageClass")
        self.assertEqual(storage["reclaimPolicy"], "Retain")
        self.assertEqual(
            storage["metadata"]["annotations"]["storageclass.kubernetes.io/is-default-class"],
            "false",
        )
        self.assertEqual(storage["parameters"], {"numberOfReplicas": "3", "share": "true"})
        project = next(
            d
            for d in documents("argocd-provision")
            if d["kind"] == "AppProject" and d["metadata"]["name"] == "agents-storage"
        )
        self.assertEqual(
            project["spec"]["clusterResourceWhitelist"],
            [{"group": "storage.k8s.io", "kind": "StorageClass"}],
        )
        self.assertEqual(project["spec"]["namespaceResourceWhitelist"], [])

    def test_provision_cannot_activate_runtime_or_adopt_other_namespaces(self):
        docs = documents("provision")
        self.assertTrue(
            all(
                d["kind"]
                in {
                    "Namespace",
                    "PersistentVolumeClaim",
                    "ServiceAccount",
                    "Role",
                    "RoleBinding",
                    "NetworkPolicy",
                }
                for d in docs
            )
        )
        self.assertEqual(
            [d["metadata"]["name"] for d in docs if d["kind"] == "Namespace"], ["agents"]
        )
        claims = [d for d in docs if d["kind"] == "PersistentVolumeClaim"]
        self.assertEqual(
            {d["metadata"]["name"] for d in claims}, {"agents-evidence", "agents-restore-test"}
        )
        for claim in claims:
            self.assertEqual(claim["spec"]["storageClassName"], "agents-evidence-rwx-retain")
            self.assertEqual(claim["spec"]["accessModes"], ["ReadWriteMany"])
        for d in docs:
            if d["kind"] != "NetworkPolicy":
                self.assertTrue(
                    {"Prune=false", "Delete=false"}
                    <= set(
                        d["metadata"]["annotations"]["argocd.argoproj.io/sync-options"].split(",")
                    )
                )
        policy = next(d["spec"] for d in docs if d["kind"] == "NetworkPolicy")
        self.assertEqual(policy["podSelector"], {})
        self.assertEqual(policy["ingress"], [])
        self.assertEqual(policy["egress"], [])

    def test_intake_role_has_no_secrets_lists_or_workload_writes(self):
        role = next(d for d in documents("provision") if d["kind"] == "Role")
        permissions = {
            (group, resource, verb)
            for rule in role["rules"]
            for group in rule["apiGroups"]
            for resource in rule["resources"]
            for verb in rule["verbs"]
        }
        self.assertEqual(
            permissions,
            {("", "pods", "get"), ("batch", "jobs", "get"), ("", "pods/exec", "create")},
        )
        sa = next(d for d in documents("provision") if d["kind"] == "ServiceAccount")
        self.assertFalse(sa["automountServiceAccountToken"])


if __name__ == "__main__":
    unittest.main()
