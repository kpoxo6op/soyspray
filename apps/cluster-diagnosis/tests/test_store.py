import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

APP = Path(__file__).parents[1] / "app"
sys.path.insert(0, str(APP))
SPEC = importlib.util.spec_from_file_location("cluster_diagnosis_store", APP / "store.py")
store = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(store)


class LockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_one_writer_can_hold_the_lock(self):
        first = store.StateStore(self.root / "state.json", self.root / "state.lock")
        second = store.StateStore(self.root / "state.json", self.root / "state.lock")
        self.assertTrue(first.acquire())
        try:
            self.assertFalse(second.acquire())
        finally:
            first.release()
        self.assertTrue(second.acquire())
        second.release()

    def test_release_allows_a_later_holder(self):
        first = store.StateStore(self.root / "state.json")
        self.assertTrue(first.acquire())
        first.release()
        self.assertTrue(first.acquire())
        first.release()


class LoadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.json"
        self.store = store.StateStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_missing_file_starts_empty(self):
        state = self.store.load()
        self.assertEqual(state["version"], store.SCHEMA_VERSION)
        self.assertEqual(state["incidents"], {})
        self.assertEqual(state["outbox"], [])

    def test_a_corrupt_file_is_unusable(self):
        self.path.write_text("{not json")
        with self.assertRaises(store.StateUnusable):
            self.store.load()

    def test_an_incompatible_schema_is_unusable(self):
        self.path.write_text(json.dumps({"version": 2, "incidents": {}}))
        with self.assertRaises(store.StateUnusable):
            self.store.load()

    def test_a_missing_key_is_filled_in(self):
        self.path.write_text(json.dumps({"version": store.SCHEMA_VERSION}))
        state = self.store.load()
        self.assertEqual(state["outbox"], [])

    def test_save_is_private_and_atomic(self):
        state = self.store.load()
        state["incidents"]["a"] = {"anchor": "app:x"}
        self.store.save(state)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.store.load()["incidents"]["a"]["anchor"], "app:x")
        leftovers = [item.name for item in self.path.parent.iterdir() if item.name.startswith(".")]
        self.assertEqual(leftovers, [])

    def test_reset_replaces_incident_and_delivery_state(self):
        state = self.store.load()
        state["outbox"] = [{"message": "pending"}]
        self.store.save(state)
        fresh = self.store.reset()
        self.assertEqual(fresh["outbox"], [])
        self.assertEqual(self.store.load()["outbox"], [])
