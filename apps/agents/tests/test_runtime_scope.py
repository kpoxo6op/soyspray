"""Static release boundaries not owned by archive or controller-selection tests."""

import re
import unittest

from test_storage_scope import documents


class RuntimeScope(unittest.TestCase):
    def test_runtime_cannot_change_storage_or_gain_credentials_or_egress(self):
        docs = documents("manifests")
        allowed = {"Job", "Deployment", "Service", "Ingress", "NetworkPolicy", "PrometheusRule"}
        self.assertTrue(all(d["kind"] in allowed for d in docs))
        workloads = [d for d in docs if d["kind"] in {"Job", "Deployment"}]
        for workload in workloads:
            pod = workload["spec"]["template"]["spec"]
            self.assertFalse(pod["automountServiceAccountToken"])
            self.assertFalse(pod["enableServiceLinks"])
            self.assertTrue(pod["securityContext"]["runAsNonRoot"])
            for container in pod.get("initContainers", []) + pod["containers"]:
                self.assertRegex(
                    container["image"], r"^ghcr\.io/kpoxo6op/agents@sha256:[a-f0-9]{64}$"
                )
                self.assertFalse(container["securityContext"]["allowPrivilegeEscalation"])
                self.assertTrue(container["securityContext"]["readOnlyRootFilesystem"])
                self.assertEqual(container["securityContext"]["capabilities"]["drop"], ["ALL"])
                self.assertFalse(container.get("envFrom"))
            self.assertTrue(
                all(set(v) <= {"name", "emptyDir", "persistentVolumeClaim"} for v in pod["volumes"])
            )
        web = next(d for d in workloads if d["kind"] == "Deployment")
        pod = web["spec"]["template"]["spec"]
        self.assertNotIn("fsGroup", pod["securityContext"])
        claims = [
            v["persistentVolumeClaim"] for v in pod["volumes"] if "persistentVolumeClaim" in v
        ]
        self.assertEqual(claims, [{"claimName": "agents-evidence", "readOnly": True}])
        self.assertEqual(web["spec"]["strategy"]["rollingUpdate"]["maxUnavailable"], 0)
        policy = next(d for d in docs if d["kind"] == "NetworkPolicy")
        self.assertEqual(policy["spec"]["egress"], [])
        project = next(d for d in documents("argocd") if d["kind"] == "AppProject")
        self.assertEqual(project["spec"]["clusterResourceWhitelist"], [])
        self.assertEqual(
            {d["kind"] for d in project["spec"]["namespaceResourceWhitelist"]}, allowed
        )

    def test_hook_lifecycle_preserves_evidence_and_blocks_web_until_intake(self):
        jobs = [d for d in documents("manifests") if d["kind"] == "Job"]
        self.assertEqual(len(jobs), 2)
        by_hook = {d["metadata"]["annotations"]["argocd.argoproj.io/hook"]: d for d in jobs}
        self.assertEqual(set(by_hook), {"Sync", "PostSync"})
        for kind, job in by_hook.items():
            annotations = job["metadata"]["annotations"]
            self.assertEqual(
                annotations["argocd.argoproj.io/hook-delete-policy"], "BeforeHookCreation"
            )
            self.assertNotIn("generateName", job["metadata"])
            self.assertNotIn("ttlSecondsAfterFinished", job["spec"])
            self.assertEqual(job["spec"]["backoffLimit"], 0)
            self.assertGreater(job["spec"]["activeDeadlineSeconds"], 0)
            if kind == "Sync":
                self.assertLess(int(annotations["argocd.argoproj.io/sync-wave"]), 0)
            expected = "agents-evidence" if kind == "Sync" else "agents-restore-test"
            volumes = job["spec"]["template"]["spec"]["volumes"]
            self.assertEqual(
                [
                    v["persistentVolumeClaim"]["claimName"]
                    for v in volumes
                    if "persistentVolumeClaim" in v
                ],
                [expected],
            )

    def test_private_host_does_not_publish_external_dns_records(self):
        ingress = next(d for d in documents("manifests") if d["kind"] == "Ingress")
        annotations = ingress["metadata"]["annotations"]
        self.assertFalse(any(re.search(r"external-dns.*hostname$", k) for k in annotations))
        for prefix in ("external-dns.alpha.kubernetes.io", "external-dns.kubernetes.io"):
            self.assertEqual(annotations[prefix + "/ingress-hostname-source"], "annotation-only")


if __name__ == "__main__":
    unittest.main()
