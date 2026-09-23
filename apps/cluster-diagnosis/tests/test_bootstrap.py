import unittest
from pathlib import Path

import yaml

TASKS = Path(__file__).parents[1] / "bootstrap-tasks.yml"
RETIREMENT = Path(__file__).parents[1] / "retire-provider-secret.yml"
RESET = Path(__file__).parents[1] / "reset-state.yml"


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
        self.assertEqual(len(reads), 1)
        for task in reads:
            command = task["ansible.builtin.command"]["argv"]
            self.assertEqual(command[:1], ["kubectl"])
            self.assertIn("get", command)
            self.assertEqual(command[-2:], ["--output", "json"])
            self.assertTrue(task["no_log"])
            self.assertFalse(task["changed_when"])
            self.assertFalse(task["check_mode"])
            self.assertFalse(task["failed_when"])

    def test_the_delivery_identity_must_be_readable(self):
        guard = next(
            task
            for task in tasks()
            if task.get("name") == "Require the existing Alertmanager bot identity"
        )
        that = guard["ansible.builtin.assert"]["that"]
        self.assertIn("cluster_diagnosis_telegram.rc == 0", that)
        self.assertIn("PROMETHEUS_TELEGRAM_BOT_TOKEN", " ".join(that))

    def test_bootstrap_never_writes_a_secret(self):
        self.assertFalse(
            [task for task in tasks() if "create" in str(task.get("ansible.builtin.command", {}))]
        )

    def test_retirement_targets_only_the_dedicated_provider_secret(self):
        play = yaml.safe_load(RETIREMENT.read_text())[0]
        self.assertEqual(play["vars"]["retired_secret"], "cluster-diagnosis-deepseek")
        deletes = [
            task
            for task in play["tasks"]
            if "delete" in (task.get("ansible.builtin.command") or {}).get("argv", [])
        ]
        self.assertEqual(len(deletes), 1)
        self.assertEqual(deletes[0]["ansible.builtin.command"]["argv"][-1], "{{ retired_secret }}")
        self.assertIn("not ansible_check_mode", deletes[0]["when"])

    def test_state_reset_requires_a_parked_writer_and_existing_claim(self):
        play = yaml.safe_load(RESET.read_text())[0]
        text = str(play["tasks"])
        self.assertIn("state_reset_confirm", text)
        self.assertIn("spec.replicas", text)
        self.assertIn("diagnosis_pods.stdout", text)
        self.assertIn("claimName: cluster-diagnosis-state", text)
        self.assertNotIn("alertmanager-telegram-secret", text)


if __name__ == "__main__":
    unittest.main()
