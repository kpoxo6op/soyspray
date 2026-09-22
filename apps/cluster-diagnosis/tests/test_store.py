import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

APP = Path(__file__).parents[1] / "app"
sys.path.insert(0, str(APP))
SPEC = importlib.util.spec_from_file_location("cluster_diagnosis_store", APP / "store.py")
store = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(store)

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


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
        self.assertEqual(state["budget"], {})

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
        self.assertIsNone(state["blocked"])

    def test_save_is_private_and_atomic(self):
        state = self.store.load()
        state["incidents"]["a"] = {"anchor": "app:x"}
        self.store.save(state)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.store.load()["incidents"]["a"]["anchor"], "app:x")
        leftovers = [item.name for item in self.path.parent.iterdir() if item.name.startswith(".")]
        self.assertEqual(leftovers, [])

    def test_reset_replaces_the_ledger(self):
        state = self.store.load()
        state["budget"] = {"2026-09-22": {"attempts": 3, "tokens": 900}}
        self.store.save(state)
        fresh = self.store.reset()
        self.assertEqual(fresh["budget"], {})
        self.assertEqual(self.store.load()["budget"], {})


class ReservationTests(unittest.TestCase):
    def test_a_reservation_counts_before_the_request(self):
        state = store.empty_state()
        allowed, why = store.reserve(state, "2026-09-22", tokens=1000)
        self.assertTrue(allowed)
        self.assertEqual(why, "")
        self.assertEqual(store.budget_for(state, "2026-09-22"), {"attempts": 1, "tokens": 1000})

    def test_the_attempt_limit_stops_further_reservations(self):
        state = store.empty_state()
        for _ in range(3):
            allowed, _ = store.reserve(state, "2026-09-22", tokens=10, attempt_limit=3)
            self.assertTrue(allowed)
        allowed, why = store.reserve(state, "2026-09-22", tokens=10, attempt_limit=3)
        self.assertFalse(allowed)
        self.assertEqual(why, "daily-attempts")
        self.assertEqual(store.budget_for(state, "2026-09-22")["attempts"], 3)

    def test_the_token_ceiling_stops_further_reservations(self):
        state = store.empty_state()
        allowed, _ = store.reserve(state, "2026-09-22", tokens=900, token_limit=1000)
        self.assertTrue(allowed)
        allowed, why = store.reserve(state, "2026-09-22", tokens=200, token_limit=1000)
        self.assertFalse(allowed)
        self.assertEqual(why, "daily-tokens")

    def test_each_day_has_its_own_budget(self):
        state = store.empty_state()
        store.reserve(state, "2026-09-22", tokens=10, attempt_limit=1)
        allowed, _ = store.reserve(state, "2026-09-23", tokens=10, attempt_limit=1)
        self.assertTrue(allowed)

    def test_a_reported_usage_replaces_the_reservation(self):
        state = store.empty_state()
        store.reserve(state, "2026-09-22", tokens=6000)
        store.charge_tokens(state, "2026-09-22", reserved=6000, used=812)
        self.assertEqual(store.budget_for(state, "2026-09-22")["tokens"], 812)

    def test_an_ambiguous_outcome_keeps_the_reservation(self):
        state = store.empty_state()
        store.reserve(state, "2026-09-22", tokens=6000)
        store.charge_tokens(state, "2026-09-22", reserved=6000, used=0)
        self.assertEqual(store.budget_for(state, "2026-09-22")["tokens"], 0)
        # The attempt itself stays spent even when no usage was reported.
        self.assertEqual(store.budget_for(state, "2026-09-22")["attempts"], 1)

    def test_a_corrupt_counter_is_repaired_not_trusted(self):
        state = store.empty_state()
        state["budget"]["2026-09-22"] = {"attempts": "lots", "tokens": None}
        entry = store.budget_for(state, "2026-09-22")
        self.assertEqual(entry, {"attempts": 0, "tokens": 0})

    def test_day_key_uses_the_auckland_date(self):
        self.assertEqual(store.day_key(NOW), "2026-09-22")

    def test_the_file_survives_a_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.json"
            handle = store.StateStore(path)
            state = handle.load()
            store.reserve(state, "2026-09-22", tokens=1500)
            handle.save(state)
            self.assertEqual(handle.load()["budget"]["2026-09-22"]["tokens"], 1500)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
