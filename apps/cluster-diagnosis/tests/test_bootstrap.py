import unittest
from pathlib import Path

import yaml

TASKS = Path(__file__).parents[1] / "bootstrap-tasks.yml"


def tasks():
    return yaml.safe_load(TASKS.read_text())


class BootstrapTest(unittest.TestCase):
    """The bootstrap runs on a control-plane node, so it must not need a Python client.

    kubernetes.core.k8s_info and kubernetes.core.k8s need the Python kubernetes
    client on the target host. The cluster nodes do not have it, so those
    modules fail with "Failed to import the required Python library" and the
    documented setup cannot run. kubectl is installed by Kubespray there.
    """

    def test_no_task_requires_the_python_kubernetes_client(self):
        modules = [name for task in tasks() for name in task if "." in name]
        self.assertEqual([name for name in modules if name.startswith("kubernetes.core")], [])

    def test_the_reads_use_kubectl_and_report_their_exit_code(self):
        reads = [
            task for task in tasks() if task.get("register", "").startswith("cluster_diagnosis_")
        ]
        self.assertEqual(len(reads), 2)
        for task in reads:
            command = task["ansible.builtin.command"]["argv"]
            self.assertEqual(command[:1], ["kubectl"])
            self.assertIn("get", command)
            self.assertEqual(command[-2:], ["--output", "json"])
            self.assertTrue(task["no_log"])
            self.assertFalse(task["changed_when"])
            self.assertFalse(task["check_mode"])
            self.assertFalse(task["failed_when"])

    def test_only_a_missing_diagnosis_secret_is_tolerated(self):
        guard = next(
            task for task in tasks() if task.get("name") == "Require a readable diagnosis namespace"
        )
        condition = " ".join(guard["ansible.builtin.assert"]["that"])
        self.assertIn("cluster_diagnosis_existing_secret.rc == 0", condition)
        self.assertIn("NotFound", condition)

    def test_the_delivery_identity_must_be_readable(self):
        guard = next(
            task
            for task in tasks()
            if task.get("name") == "Require the existing Alertmanager bot identity"
        )
        that = guard["ansible.builtin.assert"]["that"]
        self.assertIn("cluster_diagnosis_telegram.rc == 0", that)
        self.assertIn("PROMETHEUS_TELEGRAM_BOT_TOKEN", " ".join(that))

    def test_the_write_waits_for_an_absent_secret_and_real_mode(self):
        writes = [
            task for task in tasks() if "create" in str(task.get("ansible.builtin.command", {}))
        ]
        self.assertEqual(len(writes), 1)
        condition = writes[0]["when"]
        self.assertIn("cluster_diagnosis_existing_secret.rc != 0", condition)
        self.assertIn("not ansible_check_mode", condition)
        self.assertTrue(writes[0]["no_log"])


if __name__ == "__main__":
    unittest.main()
