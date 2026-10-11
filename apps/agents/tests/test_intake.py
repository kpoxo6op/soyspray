import copy
import importlib.util
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "operations/intake.py"
spec = importlib.util.spec_from_file_location("intake_guard", SOURCE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class IntakeScope(unittest.TestCase):
    def setUp(self):
        self.promotion = {
            "claimName": "agents-evidence",
            "pvcUid": "claim-uid",
            "jobName": "agents-intake-" + "a" * 16,
            "image": "ghcr.io/kpoxo6op/agents@sha256:" + "b" * 64,
            "packHash": "a" * 64,
            "archiveHash": "c" * 64,
            "archiveBytes": 123,
        }
        self.pvc = {
            "metadata": {"name": "agents-evidence", "uid": "claim-uid"},
            "spec": {"storageClassName": "agents-evidence-rwx-retain"},
            "status": {"phase": "Bound"},
        }
        self.job = {"metadata": {"name": self.promotion["jobName"], "uid": "job-uid"}}
        self.pod = {
            "metadata": {
                "ownerReferences": [
                    {
                        "controller": True,
                        "kind": "Job",
                        "uid": "job-uid",
                        "name": self.promotion["jobName"],
                    }
                ],
                "labels": {
                    "app.kubernetes.io/name": "agents-intake",
                    "agents.soyspray.vip/pack": "a" * 16,
                },
            },
            "spec": {
                "nodeName": "node-test",
                "serviceAccountName": "agents-intake-operator",
                "automountServiceAccountToken": False,
                "volumes": [
                    {"name": "evidence", "persistentVolumeClaim": {"claimName": "agents-evidence"}}
                ],
                "containers": [
                    {
                        "name": "receiver",
                        "image": self.promotion["image"],
                        "command": ["python3", "/opt/evidence.py", "receive"],
                        "volumeMounts": [{"name": "evidence", "mountPath": "/evidence"}],
                        "env": [
                            {"name": "PACK_HASH", "value": "a" * 64},
                            {"name": "ARCHIVE_HASH", "value": "c" * 64},
                            {"name": "ARCHIVE_BYTES", "value": "123"},
                        ],
                    }
                ],
            },
            "status": {"phase": "Running"},
        }

    def test_matching_receiver_is_accepted(self):
        guard.assert_target(self.promotion, self.pvc, self.job, self.pod)

    def test_completed_hook_is_accepted_only_when_both_job_and_pod_succeeded(self):
        self.pod["status"]["phase"] = "Succeeded"
        with self.assertRaises(ValueError):
            guard.assert_target(self.promotion, self.pvc, self.job, self.pod, allow_completed=True)
        self.job["status"] = {"succeeded": 1}
        guard.assert_target(self.promotion, self.pvc, self.job, self.pod, allow_completed=True)
        with self.assertRaises(ValueError):
            guard.assert_target(self.promotion, self.pvc, self.job, self.pod)

    def test_wrong_identity_or_authority_aborts_before_exec(self):
        # The receiver tests cannot own controller pod selection or namespace capability guards.
        changes = [
            lambda pvc, job, pod: pod["spec"].update(serviceAccountName="foreign"),
            lambda pvc, job, pod: pvc["metadata"].update(uid="foreign-claim"),
            lambda pvc, job, pod: pod["metadata"]["ownerReferences"][0].update(uid="foreign-job"),
            lambda pvc, job, pod: pod["metadata"]["labels"].update(
                {"app.kubernetes.io/name": "foreign-app"}
            ),
            lambda pvc, job, pod: pod["spec"]["containers"][0].update(
                image="ghcr.io/kpoxo6op/agents:mutable"
            ),
            lambda pvc, job, pod: pod["status"].update(phase="Pending"),
            lambda pvc, job, pod: pod["spec"].update(automountServiceAccountToken=True),
            lambda pvc, job, pod: pod["spec"]["containers"][0]["env"][0].update(value="d" * 64),
            lambda pvc, job, pod: pod["spec"]["containers"][0]["env"][1].update(value="e" * 64),
            lambda pvc, job, pod: pod["spec"]["containers"][0].update(command=["sh"]),
            lambda pvc, job, pod: pod["spec"]["volumes"][0]["persistentVolumeClaim"].update(
                claimName="foreign-data"
            ),
        ]
        for index, change in enumerate(changes):
            with self.subTest(mismatch=index):
                pvc, job, pod = copy.deepcopy((self.pvc, self.job, self.pod))
                change(pvc, job, pod)
                with self.assertRaises(ValueError):
                    guard.assert_target(self.promotion, pvc, job, pod)

    def test_receiver_path_and_credentials_cannot_be_substituted(self):
        # Claim-name checks alone do not prove that /evidence uses that claim,
        # or exclude manually projected credentials and extra execution paths.
        changes = [
            lambda p: p["spec"]["containers"][0]["volumeMounts"][0].update(name="scratch"),
            lambda p: p["spec"]["containers"][0]["volumeMounts"][0].update(subPath="foreign"),
            lambda p: p["spec"]["volumes"].append({"name": "token", "projected": {"sources": []}}),
            lambda p: p["spec"].update(initContainers=[{"name": "other"}]),
            lambda p: p["spec"]["containers"][0].update(envFrom=[{"secretRef": {"name": "other"}}]),
        ]
        for change in changes:
            pod = copy.deepcopy(self.pod)
            change(pod)
            with self.assertRaises(ValueError):
                guard.assert_target(self.promotion, self.pvc, self.job, pod)


class InstalledSDKContract(unittest.TestCase):
    def test_real_sdk_builds_pod_bound_token_and_attaches_only_scoped_bearer(self):
        # Dict-only pod guards cannot catch SDK model or auth-scheme changes:
        # a missing bearer header becomes anonymous, while a retained admin
        # certificate would silently defeat the intended capability boundary.
        from kubernetes import client

        pod = {"metadata": {"name": "receiver-test", "uid": "receiver-uid"}}
        body = client.ApiClient().sanitize_for_serialization(guard.token_request(pod))
        self.assertEqual(body["spec"]["boundObjectRef"]["uid"], "receiver-uid")
        self.assertEqual(body["spec"]["boundObjectRef"]["kind"], "Pod")
        self.assertLessEqual(body["spec"]["expirationSeconds"], 1800)
        base = client.Configuration()
        base.cert_file, base.key_file = "admin-cert", "admin-key"
        base.username, base.password = "admin", "admin-password-fixture"
        base.api_key = {"BearerToken": "admin-token-fixture"}
        base.debug = True
        operator = guard.operator_configuration(base, "scoped-token-fixture")
        auth = operator.auth_settings()["BearerToken"]
        self.assertEqual(auth["key"], "authorization")
        self.assertEqual(auth["value"], "Bearer scoped-token-fixture")
        for field in ("cert_file", "key_file", "username", "password", "refresh_api_key_hook"):
            self.assertIsNone(getattr(operator, field))
        self.assertFalse(operator.debug)
        self.assertEqual(base.cert_file, "admin-cert")


if __name__ == "__main__":
    unittest.main()
