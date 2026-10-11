"""Recovery must not terminate a newer, foreign, or already finished operation."""

import copy
import unittest

from operations.retire_stale_sync import termination_patch


class StaleSyncScope(unittest.TestCase):
    def setUp(self):
        self.expected = {
            "applicationUid": "reviewed-app",
            "applicationResourceVersion": "17",
            "operationStartedAt": "reviewed-start",
        }
        self.app = {
            "metadata": {
                "name": "agents",
                "namespace": "argocd",
                "uid": "reviewed-app",
                "resourceVersion": "17",
            },
            "spec": {
                "source": {
                    "repoURL": "https://github.com/kpoxo6op/soyspray.git",
                    "targetRevision": "main",
                    "path": "apps/agents/manifests",
                },
                "syncPolicy": {},
            },
            "status": {
                "sync": {"revision": "new-main"},
                "operationState": {
                    "phase": "Running",
                    "startedAt": "reviewed-start",
                    "retryCount": 4,
                    "syncResult": {"revision": "808c39d95657413ff3282f8d03edc17edb345d4e"},
                },
            },
        }

    def test_only_matching_obsolete_operation_yields_status_only_request(self):
        self.assertEqual(
            termination_patch(self.app, self.expected, "new-main"),
            {
                "metadata": {"resourceVersion": "17"},
                "status": {"operationState": {"phase": "Terminating"}},
            },
        )

    def test_new_or_changed_operation_cannot_be_terminated(self):
        changes = [
            lambda a: a["metadata"].update(uid="foreign"),
            lambda a: a["metadata"].update(resourceVersion="18"),
            lambda a: a["spec"]["source"].update(targetRevision="topic"),
            lambda a: a["status"]["sync"].update(revision="other"),
            lambda a: a["status"]["operationState"].update(phase="Succeeded"),
            lambda a: a["status"]["operationState"].update(startedAt="new-start"),
            lambda a: a["status"]["operationState"].update(retryCount=5),
            lambda a: a["status"]["operationState"]["syncResult"].update(revision="new-main"),
            lambda a: a["spec"]["syncPolicy"].update(retry={"limit": 4}),
        ]
        for change in changes:
            with self.subTest(change=change):
                app = copy.deepcopy(self.app)
                change(app)
                with self.assertRaises(ValueError):
                    termination_patch(app, self.expected, "new-main")
